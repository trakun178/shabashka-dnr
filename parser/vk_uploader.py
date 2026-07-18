import requests
import time
import os

class VKUploader:
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
        vk_photo_urls = []  # Массив для хранения URL всех загруженных фото
        
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
                temp_file = f"temp_{int(time.time())}_{index}.jpg"
                try:
                    print(f"[{index}] Скачиваем фото...")
                    img = requests.get(photo_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                    if img.status_code != 200:
                        continue
                    
                    with open(temp_file, "wb") as f:
                        f.write(img.content)
                    
                    upload_server = self._api_call("photos.getWallUploadServer", {"group_id": self.group_id})
                    if not upload_server:
                        continue
                    
                    with open(temp_file, "rb") as f:
                        upload_response = requests.post(upload_server["upload_url"], files={"photo": f}, timeout=60).json()
                    
                    if "error" in upload_response or not all(x in upload_response for x in ("server", "photo", "hash")):
                        continue
                    
                    saved = self._api_call("photos.saveWallPhoto", {
                        "group_id": self.group_id,
                        "server": upload_response["server"],
                        "photo": upload_response["photo"],
                        "hash": upload_response["hash"],
                    })
                    
                    if saved and len(saved) > 0:
                        photo = saved[0]
                        attachment = f"photo{photo['owner_id']}_{photo['id']}"
                        attachments.append(attachment)
                        
                        if "sizes" in photo and photo["sizes"]:
                            largest_size = max(photo["sizes"], key=lambda x: x.get("width", 0))
                            vk_photo_urls.append(largest_size["url"])
                            
                        print(f"✅ Фото сохранено: {attachment}")
                except Exception as e:
                    print(f"❌ Ошибка загрузки фото: {e}")
                finally:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
        
        if not attachments and photo_urls:
            print("❌ Не удалось загрузить ни одной фотографии")
            return None
            
        print("📝 Создаем запись на стене...")
        # from_group=1 гарантирует публикацию ОТ ИМЕНИ ГРУППЫ, а не админа
        post_params = {"owner_id": owner_id, "from_group": 1, "message": full_message[:4096]}
        if attachments:
            post_params["attachments"] = ",".join(attachments)
            
        post = self._api_call("wall.post", post_params)
        if not post:
            return None
            
        post_url = f"https://vk.com/wall{owner_id}_{post['post_id']}"
        print(f"✅ Пост опубликован: {post_url}")
        
        return {
            "post_id": post["post_id"],
            "post_url": post_url,
            "photo_urls": vk_photo_urls,  # Возвращаем ВСЕ URL
            "photo_url": vk_photo_urls[0] if vk_photo_urls else None,
            "attachments": attachments,
        }