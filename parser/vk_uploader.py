import io
import os
import time

import requests

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

VK_MAX_PHOTO_BYTES = 5 * 1024 * 1024  # лимит VK на одно фото
VK_MAX_SIDE = 1280                    # родной максимум VK для ленты
VK_API_VERSION = "5.199"

# upload_url живёт у VK ограниченное время; переиспользуем его,
# вместо того чтобы дёргать getWallUploadServer на каждое фото
UPLOAD_URL_TTL = 15 * 60


def normalize_image(content: bytes) -> bytes:
    """Перекодирует фото в чистый baseline JPEG: новый "холст" (без ICC/EXIF),
    RGB, сторона <= 1280 px, вес <= 5 МБ. Используется и парсером напрямую."""
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

        if max(img.size) > VK_MAX_SIDE:
            img.thumbnail((VK_MAX_SIDE, VK_MAX_SIDE), Image.LANCZOS)

        clean = Image.new("RGB", img.size, (255, 255, 255))
        clean.paste(img, (0, 0))

        buf = io.BytesIO()
        quality = 90
        while True:
            buf.seek(0)
            buf.truncate()
            clean.save(buf, format="JPEG", quality=quality,
                       optimize=True, progressive=False)
            if buf.tell() <= VK_MAX_PHOTO_BYTES or quality <= 50:
                break
            quality -= 10

        print(f"🖼 Фото перекодировано: {len(content)} -> {buf.tell()} байт "
              f"(было: {original_format}/{original_mode}, "
              f"{orig_w}x{orig_h} -> {clean.size[0]}x{clean.size[1]})")
        return buf.getvalue()
    except Exception as e:
        print(f"⚠️ Не удалось перекодировать фото ({e}) — отправляем как есть")
        return content


class FloodBlocked(Exception):
    """VK ответил Error 9. Дальше в этом запуске к VK не ходим вообще."""


class VKUploader:
    """Публикация постов с фотографиями в группу ВКонтакте.

    Правила против Error 9:
    * upload_url берём ОДИН раз и переиспользуем для всех фото поста;
    * ретраев не больше одного уровня — вложенные циклы запрещены;
    * после первой девятки ни один запрос к VK больше не уходит;
    * album_id передаётся снаружи и хранится в БД — createAlbum не повторяется;
    * если ключу недоступны ни стена, ни альбом (Error 27) — не долбим
      getAlbums/createAlbum на каждом фото, пост уходит текстом со ссылкой.
    """

    ALBUM_TITLE = "Фото объявлений (сайт)"
    MIN_API_INTERVAL = 0.4          # не больше ~2.5 запросов в секунду

    def __init__(self, token, group_id=None,
                 source_name="Шабашка DNR, Донецк, Макеевка",
                 album_id=None, on_album_created=None):
        self.token = token
        # группа могла прийти как "-203412616" — в параметрах методов
        # VK ждёт положительный group_id
        self.group_id = str(abs(int(group_id))) if group_id else None
        self.api_url = "https://api.vk.com/method"
        self.source_name = source_name
        self.flood_blocked = False
        self.flood_method = None
        self.use_album_upload = False
        self.album_unavailable = False
        self.album_id = album_id
        self.on_album_created = on_album_created   # колбэк, чтобы сохранить id в БД
        self.last_error_code = None
        self._last_call_ts = 0.0
        self._upload_cache = None                  # (url, route, ts)
        print(f"✅ VK uploader инициализирован (группа: {self.group_id}, альбом: {self.album_id})")

    # ────────────────────────── низкий уровень ──────────────────────────

    def _api_call(self, method, params=None):
        """Вызов метода VK. После Error 9 запросы вообще не отправляются:
        каждое лишнее обращение продлевает окно флуд-контроля."""
        if self.flood_blocked:
            print(f"⛔ Пропускаем {method}: VK уже вернул Error 9 на {self.flood_method}")
            return None

        # мягкий рейт-лимит
        delta = time.time() - self._last_call_ts
        if delta < self.MIN_API_INTERVAL:
            time.sleep(self.MIN_API_INTERVAL - delta)

        if params is None:
            params = {}
        params["access_token"] = self.token
        params["v"] = VK_API_VERSION
        try:
            response = requests.post(f"{self.api_url}/{method}", data=params, timeout=30)
            data = response.json()
        except Exception as e:
            print(f"⚠️ Сетевая ошибка на {method}: {e}")
            self.last_error_code = None
            return None
        finally:
            self._last_call_ts = time.time()

        if "error" in data:
            err = data["error"]
            self.last_error_code = err.get("error_code")
            msg = err.get("error_msg", "")
            print(f"❌ VK API Error {self.last_error_code} на {method}: {msg}")
            if self.last_error_code == 9:
                self.flood_blocked = True
                self.flood_method = method
                print("⛔ Flood control. Больше ни одного запроса к VK в этом запуске.")
            return None

        self.last_error_code = None
        return data.get("response")

    # ────────────────────────── альбом ──────────────────────────

    def _ensure_album(self):
        """Ищет альбом по названию. Создаёт ТОЛЬКО если список альбомов
        реально получен и нужного там нет. При ошибках помечает маршрут
        недоступным, чтобы не долбить лимитированный createAlbum."""
        if self.album_id:
            return self.album_id
        if self.album_unavailable:
            return None

        albums = self._api_call("photos.getAlbums", {"group_id": self.group_id})
        if albums is None:
            print("❌ Список альбомов не получен — маршрут альбома помечен недоступным")
            self.album_unavailable = True
            return None

        for item in albums.get("items", []):
            if item.get("title") == self.ALBUM_TITLE:
                self.album_id = item["id"]
                print(f"ℹ️ Найден служебный альбом: {self.album_id}")
                if self.on_album_created:
                    self.on_album_created(self.album_id)
                return self.album_id

        created = self._api_call("photos.createAlbum", {
            "group_id": self.group_id,
            "title": self.ALBUM_TITLE,
            "description": "Сюда парсер складывает фото объявлений для постов на стене",
        })
        if created:
            self.album_id = created["id"]
            print(f"ℹ️ Создан служебный альбом: {self.album_id}")
            if self.on_album_created:
                self.on_album_created(self.album_id)
            return self.album_id

        self.album_unavailable = True
        return None

    # ────────────────────────── сервер загрузки ──────────────────────────

    def _get_upload_target(self):
        """Возвращает (upload_url, route). Результат кэшируется на 15 минут:
        именно частые вызовы getWallUploadServer чаще всего дают Error 9."""
        if self._upload_cache:
            url, route, ts = self._upload_cache
            if time.time() - ts < UPLOAD_URL_TTL:
                return url, route
            self._upload_cache = None

        if not self.use_album_upload:
            server = self._api_call("photos.getWallUploadServer", {"group_id": self.group_id})
            if server:
                self._upload_cache = (server.get("upload_url"), "wall", time.time())
                return self._upload_cache[0], "wall"
            if self.last_error_code == 27:
                print("ℹ️ getWallUploadServer недоступен этому ключу (Error 27) — "
                      "пробуем загрузку в альбом группы")
                self.use_album_upload = True
            else:
                return None, None

        if self.album_unavailable:
            return None, None

        album_id = self._ensure_album()
        if not album_id:
            print("⚠️ Альбом недоступен этому ключу — фото пропускаются, "
                  "пост уйдёт текстом со ссылкой на сайт")
            return None, None

        server = self._api_call("photos.getUploadServer",
                                {"group_id": self.group_id, "album_id": album_id})
        if server:
            self._upload_cache = (server.get("upload_url"), "album", time.time())
            return self._upload_cache[0], "album"
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
        return normalize_image(content)

    def _upload_one(self, temp_file):
        """Одна попытка загрузки файла. Ретрай — уровнем выше, здесь циклов нет:
        вложенные ретраи и были источником десятков запросов на альбом."""
        upload_url, route = self._get_upload_target()
        if not upload_url:
            return None, None
        try:
            with open(temp_file, "rb") as f:
                resp = requests.post(upload_url, files={"photo": f}, timeout=90)
        except Exception as e:
            print(f"⚠️ Сетевая ошибка при заливке файла: {e}")
            # upload_url мог протухнуть — сбросим кэш, но сервер не дёргаем
            self._upload_cache = None
            return None, route
        try:
            return resp.json(), route
        except ValueError:
            print(f"⚠️ Сервер загрузки вернул не JSON (код {resp.status_code}): {resp.text[:200]!r}")
            self._upload_cache = None
            return None, route

    def _process_photo(self, photo_url, index):
        """Скачивает, нормализует, грузит и сохраняет одно фото.
        Возвращает (attachment, cdn_url) или (None, None)."""
        temp_file = f"temp_{int(time.time())}_{index}.jpg"
        try:
            print(f"[{index}] Скачиваем фото...")
            img = requests.get(photo_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            if img.status_code != 200 or not img.content:
                print(f"❌ Не удалось скачать изображение (код: {img.status_code})")
                return None, None

            content_type = (img.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            print(f"   Размер: {len(img.content)} байт, Content-Type: {content_type}")

            if not content_type.startswith("image/") and not self._is_image_by_magic(img.content):
                print(f"❌ Это не изображение (Content-Type: {content_type}) — пропускаем")
                return None, None

            content = self._normalize_image(img.content)
            if len(content) > VK_MAX_PHOTO_BYTES:
                print(f"❌ Фото тяжелее 5 МБ после перекодировки ({len(content)} байт) — пропускаем")
                return None, None

            with open(temp_file, "wb") as f:
                f.write(content)

            # ровно две попытки, без вложенных циклов
            upload_response, route = None, None
            for attempt in (1, 2):
                if self.flood_blocked:
                    raise FloodBlocked()
                upload_response, route = self._upload_one(temp_file)
                if self._upload_response_ok(upload_response, route):
                    break
                if attempt == 1:
                    print("⚠️ VK не принял файл — одна повторная попытка")
                    time.sleep(3)

            if not self._upload_response_ok(upload_response, route):
                print("❌ VK так и не принял фото — пропускаем его")
                return None, None

            saved = self._save_photo(route, upload_response)
            if not saved or not isinstance(saved, list):
                print(f"❌ Сохранение фото вернуло: {saved}")
                return None, None

            photo = saved[0]
            attachment = f"photo{photo['owner_id']}_{photo['id']}"
            if photo.get("access_key"):
                attachment += f"_{photo['access_key']}"

            cdn = None
            if photo.get("sizes"):
                cdn = max(photo["sizes"], key=lambda x: x.get("width", 0))["url"]

            print(f"✅ Фото сохранено: {attachment} (маршрут: {route})")
            return attachment, cdn
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    # ────────────────────────── публикация ──────────────────────────

    def post_with_photos(self, message, photo_urls=None, forwarded_from=None,
                         post_link=None, site_link=None):
        if not self.group_id:
            print("❌ Не указан group_id")
            return None

        if self.flood_blocked:
            print("⛔ VK во флуд-контроле — пост на стену не создаём")
            return None

        owner_id = -abs(int(self.group_id))
        attachments = []
        vk_photo_urls = []

        # ✅ Ссылка на сайт идёт ПЕРВОЙ ссылкой в посте: VK построит превью
        #    с фото и описанием из OG-тегов страницы объявления
        footer_parts = [f"📢 Источник: {self.source_name}"]
        if site_link:
            footer_parts.append(f"🌐 Объявление с фото: {site_link}")
        if forwarded_from and not forwarded_from.startswith("@"):
            footer_parts.append(f"👤 Переслано от: {forwarded_from}")
        if post_link:
            footer_parts.append(f"🔗 Оригинал поста: {post_link}")

        full_message = (message or "") + "\n\n" + "🔸" * 10 + "\n" + "\n".join(footer_parts)

        if photo_urls:
            print(f"📤 Загружаем {len(photo_urls)} фото...")
            for index, photo_url in enumerate(photo_urls[:10], start=1):
                if self.flood_blocked:
                    print("⛔ Error 9 во время загрузки — прекращаем работу с фото")
                    return None
                if not photo_url or "http" not in photo_url:
                    print(f"❌ Невалидный URL фото: {photo_url}")
                    continue
                try:
                    attachment, cdn = self._process_photo(photo_url, index)
                except FloodBlocked:
                    print("⛔ Error 9 во время загрузки — пост не создаём")
                    return None
                except Exception as e:
                    print(f"❌ Ошибка обработки фото: {e}")
                    continue
                if attachment:
                    attachments.append(attachment)
                    if cdn:
                        vk_photo_urls.append(cdn)
                time.sleep(1)

        if not attachments and photo_urls:
            print("⚠️ Не удалось загрузить ни одной фотографии — публикуем пост без фото")

        if self.flood_blocked:
            print("⛔ VK во флуд-контроле — пост на стену не создаём")
            return None

        print("📝 Создаем запись на стене...")
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
            "photo_urls": vk_photo_urls,
            "photo_url": vk_photo_urls[0] if vk_photo_urls else None,
            "attachments": attachments,
        }