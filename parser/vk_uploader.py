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
    """Публикация постов с фотографиями в группу ВКонтакте."""

    VK_MAX_PHOTO_BYTES = 5 * 1024 * 1024  # лимит VK на одно фото
    VK_MAX_SIDE = 2048                    # ограничиваем сторону, чтобы точно пройти

    def __init__(self, token, group_id=None, source_name="Шабашка DNR, Донецк, Макеевка"):
        self.token = token
        self.group_id = str(group_id) if group_id else None
        self.api_url = "https://api.vk.com/method"
        self.source_name = source_name
        print(f"✅ VK uploader инициализирован (группа: {self.group_id})")

    def _api_call(self, method, params=None):
        if params is None:
            params = {}
        params["access_token"] = self.token
        params["v"] = "5.131"
        response = requests.post(f"{self.api_url}/{method}", data=params, timeout=30)
        data = response.json()
        if "error" in data:
            err = data["error"]
            print(f"❌ VK API Error {err['error_code']}: {err['error_msg']}")
            return None
        return data.get("response")

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
        """✅ Приводит фото к виду, который VK принимает ВСЕГДА:
        RGB (убирает CMYK/альфа), сторона ≤ 2048 px, JPEG ≤ 5 МБ.
        Лечит случаи «большой размер / высокое качество / странный формат»."""
        if not HAS_PIL:
            print("⚠️ Pillow не установлен — отправляем как есть")
            return content
        try:
            img = Image.open(io.BytesIO(content))
            original_mode = img.mode
            original_format = img.format
            resized = False

            if max(img.size) > self.VK_MAX_SIDE:
                img.thumbnail((self.VK_MAX_SIDE, self.VK_MAX_SIDE), Image.LANCZOS)
                resized = True

            # Маленький обычный JPEG не трогаем — не пережимаем без нужды
            if (original_format == "JPEG" and original_mode == "RGB"
                    and not resized and len(content) <= self.VK_MAX_PHOTO_BYTES):
                return content

            if img.mode != "RGB":
                img = img.convert("RGB")

            buf = io.BytesIO()
            quality = 90
            while True:
                buf.seek(0)
                buf.truncate()
                img.save(buf, format="JPEG", quality=quality, optimize=True)
                if buf.tell() <= self.VK_MAX_PHOTO_BYTES or quality <= 50:
                    break
                quality -= 10

            print(f"🖼 Фото нормализовано: {len(content)} → {buf.tell()} байт "
                  f"(формат: {original_format}, режим: {original_mode})")
            return buf.getvalue()
        except Exception as e:
            print(f"⚠️ Не удалось нормализовать фото ({e}) — отправляем как есть")
            return content

    def post_with_photos(self, message, photo_urls=None, forwarded_from=None, post_link=None):
        if not self.group_id:
            print("❌ Не указан group_id")
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
                    print(f"[{index}] Скачиваем фото...")
                    img = requests.get(photo_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                    if img.status_code != 200 or not img.content:
                        print(f"❌ Не удалось скачать изображение (код: {img.status_code})")
                        continue

                    content_type = (img.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                    is_image = content_type.startswith("image/")
                    if not is_image:
                        if self._is_image_by_magic(img.content):
                            is_image = True
                            print(f"ℹ️ Content-Type: {content_type}, но файл — картинка (magic bytes OK)")
                        else:
                            print(f"❌ Это не изображение (Content-Type: {content_type}) — пропускаем")
                            continue

                    # ✅ Нормализуем: RGB + ≤2048px + JPEG ≤5МБ
                    content = self._normalize_image(img.content)

                    if len(content) > self.VK_MAX_PHOTO_BYTES:
                        print(f"❌ Фото тяжелее 5 МБ даже после нормализации ({len(content)} байт) — пропускаем")
                        continue

                    with open(temp_file, "wb") as f:
                        f.write(content)

                    upload_server = self._api_call("photos.getWallUploadServer", {"group_id": self.group_id})
                    if not upload_server:
                        print("❌ Не получен сервер загрузки")
                        continue

                    with open(temp_file, "rb") as f:
                        upload_response = requests.post(
                            upload_server["upload_url"], files={"photo": f}, timeout=60
                        ).json()

                    print("📤 UPLOAD RESPONSE:")
                    print(upload_response)

                    if "error" in upload_response:
                        print(f"❌ Ошибка загрузки: {upload_response.get('error', 'Unknown')}")
                        continue

                    if (
                        not upload_response.get("photo")
                        or not upload_response.get("server")
                        or not upload_response.get("hash")
                    ):
                        print("❌ VK вернул пустое photo/server/hash — файл не прошёл валидацию на сервере")
                        continue

                    saved = self._api_call("photos.saveWallPhoto", {
                        "group_id": self.group_id,
                        "server": upload_response["server"],
                        "photo": upload_response["photo"],
                        "hash": upload_response["hash"],
                    })

                    print("💾 SAVE RESPONSE:")
                    print(saved)

                    if not saved:
                        print("❌ photos.saveWallPhoto вернул None")
                        continue

                    if not isinstance(saved, list) or len(saved) == 0:
                        print(f"❌ Ожидался список фото, получено: {saved}")
                        continue

                    photo = saved[0]
                    attachment = f"photo{photo['owner_id']}_{photo['id']}"
                    attachments.append(attachment)

                    if photo.get("sizes"):
                        largest = max(photo["sizes"], key=lambda x: x.get("width", 0))
                        vk_photo_urls.append(largest["url"])

                    print(f"✅ Фото сохранено: {attachment}")
                except Exception as e:
                    print(f"❌ Ошибка: {e}")
                finally:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)

        if not attachments and photo_urls:
            print("⚠️ Не удалось загрузить ни одной фотографии — публикуем пост без фото")

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