import os
import time

import requests


class VKUploader:
    """Публикация постов с фотографиями в группу ВКонтакте."""

    VK_MAX_PHOTO_BYTES = 5 * 1024 * 1024  # лимит VK на размер одного фото

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
                # Проверка URL
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

                    # ✅ ВАЛИДАЦИЯ ДО ЗАГРУЗКИ В VK: только картинки, не тяжелее 5 МБ
                    content_type = (img.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                    if not content_type.startswith("image/"):
                        print(f"❌ Это не изображение (Content-Type: {content_type}) — пропускаем")
                        continue

                    if len(img.content) > self.VK_MAX_PHOTO_BYTES:
                        print(f"❌ Фото тяжелее 5 МБ ({len(img.content)} байт) — VK не примет, пропускаем")
                        continue

                    with open(temp_file, "wb") as f:
                        f.write(img.content)

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

                    # ✅ РАНЬШЕ: 'if "photo" not in upload_response' — но VK возвращает
                    #    ключ photo с ПУСТОЙ строкой, если файл не прошёл валидацию.
                    #    Теперь пустое photo ловится и не уезжает в saveWallPhoto.
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
            # ✅ РАНЬШЕ здесь был return None — пост вообще не публиковался.
            #    Теперь публикуем текстом: лучше пост без фото, чем пропущенное объявление.
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