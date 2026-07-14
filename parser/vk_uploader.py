import requests
import time
import os

class VKUploader:
    def __init__(self, token, group_id=None):
        self.token = token
        self.group_id = str(group_id) if group_id else None
        self.api_url = "https://api.vk.com/method"
        print(f"✅ VK uploader инициализирован (группа: {self.group_id})")
    
    def _api_call(self, method, params=None):
        """Прямой вызов API VK"""
        if params is None:
            params = {}
        
        params["access_token"] = self.token
        params["v"] = "5.131"
        
        response = requests.post(
            f"{self.api_url}/{method}",
            data=params,
            timeout=30
        )
        data = response.json()
        
        if "error" in data:
            err = data["error"]
            print(f"❌ VK API Error {err['error_code']}: {err['error_msg']}")
            return None
        
        return data.get("response")
    
    def post_with_photos(self, message, photo_urls):
        """Загружаем фото и публикуем пост в группу VK"""
        if not self.group_id:
            print("❌ Не указан group_id")
            return None
        
        owner_id = -abs(int(self.group_id))
        attachments = []
        
        print(f"📤 Загружаем {len(photo_urls)} фото...")
        
        for index, photo_url in enumerate(photo_urls[:10], start=1):
            temp_file = f"temp_{int(time.time())}_{index}.jpg"
            
            try:
                print(f"\n[{index}] Скачиваем фото")
                
                # Скачиваем фото
                img = requests.get(
                    photo_url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=30,
                )
                
                if img.status_code != 200:
                    print("❌ Не удалось скачать изображение")
                    continue
                
                with open(temp_file, "wb") as f:
                    f.write(img.content)
                
                # Получаем сервер загрузки
                upload_server = self._api_call(
                    "photos.getWallUploadServer",
                    {
                        "group_id": self.group_id
                    }
                )
                
                if not upload_server:
                    continue
                
                upload_url = upload_server["upload_url"]
                print(" Загружаем в VK...")
                
                # Загружаем файл
                with open(temp_file, "rb") as f:
                    upload_response = requests.post(
                        upload_url,
                        files={"photo": f},
                        timeout=60
                    ).json()
                
                if "error" in upload_response:
                    print("❌ Ошибка загрузки файла")
                    continue
                
                required = ("server", "photo", "hash")
                if not all(x in upload_response for x in required):
                    print("❌ Некорректный ответ VK")
                    continue
                
                print("💾 Сохраняем фото...")
                
                # Сохраняем фото
                saved = self._api_call(
                    "photos.saveWallPhoto",
                    {
                        "group_id": self.group_id,
                        "server": upload_response["server"],
                        "photo": upload_response["photo"],
                        "hash": upload_response["hash"],
                    },
                )
                
                if not saved:
                    continue
                
                photo = saved[0]
                attachment = f"photo{photo['owner_id']}_{photo['id']}"
                attachments.append(attachment)
                
                # Получаем URL фото (самый большой размер)
                photo_url_vk = None
                if "sizes" in photo:
                    # Берём самое большое фото
                    largest = max(photo["sizes"], key=lambda x: x.get("width", 0))
                    photo_url_vk = largest["url"]
                
                print(f"✅ Фото сохранено: {attachment}")
                if photo_url_vk:
                    print(f"   URL: {photo_url_vk[:80]}...")
                
            except Exception as e:
                print(f"❌ {e}")
            
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
        
        if not attachments:
            print("❌ Не удалось загрузить ни одной фотографии")
            return None
        
        # Публикуем пост
        print("\n📝 Создаем запись на стене...")
        
        post = self._api_call(
            "wall.post",
            {
                "owner_id": owner_id,
                "from_group": 1,
                "message": message[:4096],
                "attachments": ",".join(attachments),
            },
        )
        
        if not post:
            print("❌ Не удалось создать пост")
            return None
        
        post_url = f"https://vk.com/wall{owner_id}_{post['post_id']}"
        print(f"✅ Пост опубликован: {post_url}")
        
        # Возвращаем результат С photo_url!
        return {
            "post_id": post["post_id"],
            "post_url": post_url,
            "photo_url": photo_url_vk if photo_url_vk else None,  # ✅ ДОБАВЛЕНО!
            "attachments": attachments,
        }