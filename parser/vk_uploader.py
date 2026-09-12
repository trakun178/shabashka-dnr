import io
import os
import time

import requests

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class VKUploader:
    """Публикация постов с фотографиями в группу ВКонтакте.

    Схема загрузки фото:
    1) Если ключ умеет photos.getWallUploadServer — грузим через него (старая схема).
    2) Если ключ отвечает Error 27 (групповые токены нового образца) —
       автоматически переключаемся на загрузку в служебный альбом группы
       (photos.getUploadServer + photos.save): такие фото прикрепляются
       к посту на стене как обычные и отдают CDN-ссылку для сайта.
    """

    VK_MAX_PHOTO_BYTES = 5 * 1024 * 1024  # лимит VK на одно фото
    VK_MAX_SIDE = 1280                    # родной максимум VK для ленты
    ALBUM_TITLE = "Фото объявлений (сайт)"

    def __init__(self, token, group_id=None, source_name="Шабашка DNR, Донецк, Макеевка"):
        self.token = token
        self.group_id = str(group_id) if group_id else None
        self.api_url = "https://api.vk.com/method"
        self.source_name = source_name
        self.flood_blocked = False
        self.use_album_upload = False
        self.album_id = None
        self.last_error_code = None
        print(f"✅ VK uploader инициализирован (группа: {self.group_id})")

    def _api_call(self, method, params=None):
        """Вызов метода VK с откатом при Error 9 (Flood control)."""
        for attempt in range(1, 4):
            if params is None:
                params = {}
            params["access_token"] = self.token
            params["v"] = "5.131"
            response = requests.post(f"{self.api_url}/{method}", data=params, timeout=30)
            data = response.json()
            if "error" in data:
                err = data["error"]
                self.last_error_code = err.get("error_code")
                if self.last_error_code == 9:
                    # Не продлеваем блокировку повторами: сразу стоп до конца запуска
                    self.flood_blocked = True
                    print(f"⛔ Flood control (Error 9) на {method} — "
                          f"VK-публикация остановлена до конца запуска")
                print(f"❌ VK API Error {self.last_error_code}: {err['error_msg']}")
                return None
            self.last_error_code = None
            return data.get("response")
        return None

    def _ensure_album(self):
        """Находит или создаёт служебный альбом группы для фото объявлений."""
        if self.album_id:
            return self.album_id
        albums = self._api_call("photos.getAlbums", {"group_id": self.group_id})
        if albums is not None:
            for item in albums.get("items", []):
                if item.get("title") == self.ALBUM_TITLE:
                    self.album_id = item["id"]
                    print(f"ℹ️ Найден служебный альбом: {self.album_id}")
                    return self.album_id
        created = self._api_call("photos.createAlbum", {
            "group_id": self.group_id,
            "title": self.ALBUM_TITLE,
            "description": "Сюда парсер складывает фото объявлений для постов на стене",
        })
        if created:
            self.album_id = created["id"]
            print(f"ℹ️ Создан служебный альбом: {self.album_id}")
        return self.album_id

    def _get_upload_target(self):
        """Возвращает (upload_url, route), route: 'wall' или 'album'."""
        if not self.use_album_upload:
            server = self._api_call("photos.getWallUploadServer", {"group_id": self.group_id})
            if server:
                return server.get("upload_url"), "wall"
            if self.last_error_code == 27:
                print("ℹ️ getWallUploadServer недоступен этому ключу (Error 27) — "
                      "переключаемся на загрузку в альбом группы")
                self.use_album_upload = True
            else:
                return None, None

        album_id = self._ensure_album()
        if not album_id:
            print("❌ Не удалось получить/создать альбом для фото")
            return None, None
        server = self._api_call("photos.getUploadServer",
                                {"group_id": self.group_id, "album_id": album_id})
        if server:
            return server.get("upload_url"), "album"
        return None, None

    @staticmethod
    def _upload_response_ok(upload_response, route):
        if not upload_response:
            return False
        if not upload_response.get("server") or not upload_response.get("hash"):
            return False
        if route == "wall":
            return bool(upload_response.get("photo"))
        return bool(upload_response.get("photos_list"))

    def _save_photo(self, route, upload_response):
        if route == "wall":
            return self._api_call("photos.saveWallPhoto", {
                "group_id": self.group_id,
                "server": upload_response["server"],
                "photo": upload_response["photo"],
                "hash": upload_response["hash"],
            })
        return self._api_call("photos.save", {
            "group_id": self.group_id,
            "album_id": self.album_id,
            "server": upload_response["server"],
            "photos_list": upload_response["photos_list"],
            "hash": upload_response["hash"],
        })

    def _is_image_by_magic(self, content):
        """Проверка по магическим байтам, если Content-Type отсутствует/неверный."""
        if not content:
            return False
        header = content[:16]
        if header.startswith(b'\xff\xd8\xff'):            # JPEG
            return True
        if header.startswith(b'\x89PNG\r\n\x1a\n'):       # PNG
            return True
        if header[:4] == b'RIFF' and b'WEBP' in header:   # WEBP
            return True
        if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):  # GIF
            return True
        return False

    def _normalize_image(self, content: bytes) -> bytes:
        """Перекодирует фото в чистый baseline JPEG: новый "холст" (без ICC/EXIF),
        RGB, сторона <= 1280 px, вес <= 5 МБ."""
        if not HAS_PIL:
            print("⚠️ Pillow не установлен — отправляем как есть")
            return content
        try:
            img = Image.open(io.BytesIO(content))
            original_format = img.format
            original_mode = img.mode
            orig_w, orig_h = img.size

            if img.mode in ("RGBA", "LA", "P"):
                rgb = Image.new("RGB", img.size, (255, 255, 255))
                rgb.paste(img, mask=img.convert("RGBA").getchannel("A"))
                img = rgb
            elif img.mode != "RGB":
                img = img.convert("RGB")

            if max(img.size) > self.VK_MAX_SIDE:
                img.thumbnail((self.VK_MAX_SIDE, self.VK_MAX_SIDE), Image.LANCZOS)

            clean = Image.new("RGB", img.size, (255, 255, 255))
            clean.paste(img, (0, 0))

            buf = io.BytesIO()
            quality = 90
            while True:
                buf.seek(0)
                buf.truncate()
                clean.save(buf, format="JPEG", quality=quality,
                           optimize=True, progressive=False)
                if buf.tell() <= self.VK_MAX_PHOTO_BYTES or quality <= 50:
                    break
                quality -= 10

            print(f"🖼 Фото перекодировано: {len(content)} -> {buf.tell()} байт "
                  f"(было: {original_format}/{original_mode}, "
                  f"{orig_w}x{orig_h} -> {clean.size[0]}x{clean.size[1]})")
            return buf.getvalue()
        except Exception as e:
            print(f"⚠️ Не удалось перекодировать фото ({e}) — отправляем как есть")
            return content

    def _upload_photo_to_server(self, temp_file):
        """Скачанный и перекодированный файл укладывается на сервер VK.
        Возвращает (response, route). До 2 попыток при сбоях."""
        for attempt in range(1, 3):
            upload_url, route = self._get_upload_target()
            if not upload_url:
                print("❌ Не получен сервер загрузки")
                return None, None

            try:
                with open(temp_file, "rb") as f:
                    resp = requests.post(upload_url, files={"photo": f}, timeout=90)
            except Exception as e:
                print(f"⚠️ Попытка {attempt}: сетевая ошибка при загрузке: {e}")
                time.sleep(5)
                continue

            try:
                return resp.json(), route
            except ValueError:
                print(f"⚠️ Попытка {attempt}: сервер VK вернул не JSON "
                      f"(код {resp.status_code}): {resp.text[:200]!r}")
                time.sleep(5)

        print("❌ Попытки загрузки не дали валидного ответа VK")
        return None, None

    def post_with_photos(self, message, photo_urls=None, forwarded_from=None, post_link=None):
        if not self.group_id:
            print("❌ Не указан group_id")
            return None

        if self.flood_blocked:
            print("⛔ VK во флуд-контроле — до конца запуска публикуем только на сайт")
            return None

        owner_id = -abs(int(self.group_id))
        attachments = []
        vk_photo_urls = []

        footer_parts = [f"📢 Источник: {self.source_name}"]
        if forwarded_from and not forwarded_from.startswith('@'):
            footer_parts.append(f"👤 Переслано от: {forwarded_from}")
        if post_link:
            footer_parts.append(f"🔗 Оригинал поста: {post_link}")

        full_message = message
        if footer_parts:
            full_message += "\n\n" + "🔸" * 10 + "\n" + "\n".join(footer_parts)

        if photo_urls:
            print(f"📤 Загружаем {len(photo_urls)} фото...")
            for index, photo_url in enumerate(photo_urls[:10], start=1):
                if not photo_url or "http" not in photo_url:
                    print(f"❌ Невалидный URL фото: {photo_url}")
                    continue

                temp_file = f"temp_{int(time.time())}_{index}.jpg"
                try:
                    # ✅ СНАЧАЛА скачиваем и форматируем под VK, потом стучимся в VK
                    print(f"[{index}] Скачиваем фото...")
                    img = requests.get(photo_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                    if img.status_code != 200 or not img.content:
                        print(f"❌ Не удалось скачать изображение (код: {img.status_code})")
                        continue

                    content_type = (img.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                    print(f"   Размер: {len(img.content)} байт, Content-Type: {content_type}")

                    is_image = content_type.startswith("image/")
                    if not is_image:
                        if self._is_image_by_magic(img.content):
                            is_image = True
                            print("ℹ️ Content-Type не image/*, но файл — картинка (magic bytes OK)")
                        else:
                            print(f"❌ Это не изображение (Content-Type: {content_type}) — пропускаем")
                            continue

                    content = self._normalize_image(img.content)

                    if len(content) > self.VK_MAX_PHOTO_BYTES:
                        print(f"❌ Фото тяжелее 5 МБ даже после перекодировки ({len(content)} байт) — пропускаем")
                        continue

                    with open(temp_file, "wb") as f:
                        f.write(content)

                    upload_response, route = None, None
                    for attempt in range(1, 3):
                        upload_response, route = self._upload_photo_to_server(temp_file)
                        if upload_response is None:
                            break
                        if self._upload_response_ok(upload_response, route):
                            break
                        print(f"⚠️ Попытка {attempt}: VK не принял файл — повторяем загрузку")
                        time.sleep(3)

                    print("📤 UPLOAD RESPONSE:")
                    print(upload_response)

                    if route is None or not self._upload_response_ok(upload_response, route):
                        print("❌ VK так и не принял фото — пропускаем его")
                        continue

                    saved = self._save_photo(route, upload_response)

                    print("💾 SAVE RESPONSE:")
                    print(saved)

                    if not saved:
                        print("❌ Сохранение фото вернуло None")
                        continue

                    if not isinstance(saved, list) or len(saved) == 0:
                        print(f"❌ Ожидался список фото, получено: {saved}")
                        continue

                    photo = saved[0]
                    attachment = f"photo{photo['owner_id']}_{photo['id']}"
                    if photo.get('access_key'):
                        attachment += f"_{photo['access_key']}"
                    attachments.append(attachment)

                    if photo.get("sizes"):
                        largest = max(photo["sizes"], key=lambda x: x.get("width", 0))
                        vk_photo_urls.append(largest["url"])

                    print(f"✅ Фото сохранено: {attachment} (маршрут: {route})")
                except Exception as e:
                    print(f"❌ Ошибка: {e}")
                finally:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)

                # ✅ Разрядка между вызовами
                time.sleep(2)

        if not attachments and photo_urls:
            print("⚠️ Не удалось загрузить ни одной фотографии — публикуем пост без фото")

            if self.flood_blocked:
               print("⛔ VK во флуд-контроле — пост на стену не создаём")
            return None

        print("📝 Создаем запись на стене...")
        time.sleep(2)
        post_params = {"owner_id": owner_id, "from_group": 1, "message": full_message[:4096]}
        if attachments:
            post_params["attachments"] = ",".join(attachments)

        post = self._api_call("wall.post", post_params)
        if not post:
            print("❌ Не удалось создать пост")
            return None

        post_url = f"https://vk.com/wall{owner_id}_{post['post_id']}"
        print(f"✅ Пост опубликован: {post_url}")

        return {
            "post_id": post["post_id"],
            "post_url": post_url,
            "photo_urls": vk_photo_urls,   # ✅ CDN VK — именно их берёт сайт (без VPN)
            "photo_url": vk_photo_urls[0] if vk_photo_urls else None,
            "attachments": attachments,
        }