import requests
import vk_api
from vk_api.upload import VkUpload
import time
import os

class VKUploader:
    def __init__(self, token, group_id=None):
        self.vk = vk_api.VkApi(token=token)
        self.group_id = group_id
        self.vk_api = self.vk.get_api()
        print(f"✅ VK uploader инициализирован (группа: {group_id})")
    
    def post_with_photos(self, message, photo_urls):
        """Загружаем фото на стену группы и публикуем пост"""
        try:
            if not self.group_id:
                print("  ❌ group_id не указан!")
                return None
            
            print(f"  📤 Загружаем {len(photo_urls)} фото в группу VK...")
            
            photo_attachments = []
            group_owner_id = -int(self.group_id)
            
            for i, photo_url in enumerate(photo_urls[:10], 1):
                print(f"    [{i}/{len(photo_urls)}] Скачиваем...")
                
                # Скачиваем фото
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(photo_url, headers=headers, timeout=15)
                
                if response.status_code != 200:
                    print(f"    ⚠️ Ошибка: {response.status_code}")
                    continue
                
                # Сохраняем временно
                temp_path = f"temp_{int(time.time())}_{i}.jpg"
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                
                # Загружаем фото ЧЕРЕЗ getWallUploadServer
                try:
                    # 1. Получаем URL для загрузки на стену
                    upload_server = self.vk_api.photos.getWallUploadServer(
                        group_id=self.group_id
                    )
                    
                    upload_url = upload_server['upload_url']
                    
                    # 2. Загружаем файл
                    with open(temp_path, 'rb') as f:
                        upload_response = requests.post(
                            upload_url,
                            files={'photo': f}
                        ).json()
                    
                    # 3. Сохраняем фото
                    saved = self.vk_api.photos.saveWallPhoto(
                        photo=upload_response['photo'],
                        hash=upload_response['hash'],
                        server=upload_response['server']
                    )
                    
                    photo_id = saved[0]['id']
                    photo_attachments.append(f"photo{group_owner_id}_{photo_id}")
                    
                    print(f"    ✅ Загружено: photo{group_owner_id}_{photo_id}")
                    
                except Exception as e:
                    print(f"    ❌ Ошибка: {str(e)[:150]}")
                
                finally:
                    try:
                        os.remove(temp_path)
                    except:
                        pass
            
            if not photo_attachments:
                print(f"  ️ Не удалось загрузить фото")
                return None
            
            # Публикуем пост
            print(f"  📝 Публикуем пост...")
            
            attachments_str = ",".join(photo_attachments)
            
            post = self.vk_api.wall.post(
                owner_id=group_owner_id,
                message=message[:4096],
                attachments=attachments_str,
                from_group=1
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