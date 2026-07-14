import requests
import vk_api
from vk_api.upload import VkUpload
import time
import os

class VKUploader:
    def __init__(self, token, group_id=None):
        self.vk = vk_api.VkApi(token=token)
        self.upload = VkUpload(self.vk)
        self.group_id = group_id
        self.vk_api = self.vk.get_api()
        print(f"✅ VK uploader инициализирован (группа: {group_id})")
    
    def post_with_photos(self, message, photo_urls):
        """Загружаем фото и публикуем пост в группу"""
        try:
            print(f"  📤 Загружаем {len(photo_urls)} фото в VK...")
            
            photo_attachments = []
            
            for i, photo_url in enumerate(photo_urls[:10], 1):
                print(f"    [{i}/{len(photo_urls)}] Скачиваем...")
                
                # Скачиваем фото
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(photo_url, headers=headers, timeout=15)
                
                if response.status_code != 200:
                    print(f"    ️ Ошибка: {response.status_code}")
                    continue
                
                # Сохраняем временно
                temp_path = f"temp_{int(time.time())}_{i}.jpg"
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                
                # Загружаем фото в группу
                try:
                    if self.group_id:
                        # Получаем URL для загрузки в группу
                        upload_url_response = self.vk_api.photos.getOwnerPhotoUploadServer(
                            group_id=self.group_id
                        )
                        
                        upload_url = upload_url_response['upload_url']
                        
                        # Загружаем фото на сервер VK
                        with open(temp_path, 'rb') as f:
                            upload_response = requests.post(
                                upload_url,
                                files={'photo': f}
                            ).json()
                        
                        # Сохраняем фото
                        saved_photo = self.vk_api.photos.saveOwnerPhoto(
                            photo=upload_response['photo'],
                            hash=upload_response['hash'],
                            server=upload_response['server']
                        )
                        
                        photo_id = saved_photo[0]['id']
                        owner_id = -int(self.group_id)  # Отрицательный для группы
                        photo_attachments.append(f"photo{owner_id}_{photo_id}")
                        
                        print(f"    ✅ Загружено: photo{owner_id}_{photo_id}")
                    else:
                        # Загружаем на личную стену
                        upload = self.upload.photo_wall(photos=[temp_path])
                        photo_id = upload[0]['id']
                        owner_id = upload[0]['owner_id']
                        photo_attachments.append(f"photo{owner_id}_{photo_id}")
                        print(f"    ✅ Загружено: photo{owner_id}_{photo_id}")
                    
                except Exception as e:
                    print(f"    ❌ Ошибка загрузки: {str(e)[:100]}")
                
                finally:
                    try:
                        os.remove(temp_path)
                    except:
                        pass
            
            if not photo_attachments:
                print(f"  ⚠️ Не удалось загрузить фото")
                return None
            
            # Публикуем пост
            print(f"   Публикуем пост...")
            
            attachments_str = ",".join(photo_attachments)
            
            # Публикуем В ГРУППУ
            if self.group_id:
                post = self.vk_api.wall.post(
                    owner_id=-int(self.group_id),
                    message=message[:4096],
                    attachments=attachments_str
                )
            else:
                post = self.vk_api.wall.post(
                    message=message[:4096],
                    attachments=attachments_str
                )
            
            post_url = f"https://vk.com/wall{post['owner_id']}_{post['post_id']}"
            print(f"  ✅ Пост создан: {post_url}")
            
            return {
                'post_id': post['post_id'],
                'post_url': post_url,
                'photo_url': None,
                'attachments': photo_attachments
            }
            
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            return None