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
        """Сразу публикуем пост с фото (загружаем и постим)"""
        try:
            print(f"  📤 Загружаем {len(photo_urls)} фото в VK...")
            
            photo_attachments = []
            
            # Загружаем каждое фото
            for i, photo_url in enumerate(photo_urls[:10], 1):
                print(f"    [{i}/{len(photo_urls)}] Скачиваем: {photo_url[:50]}...")
                
                # Скачиваем фото
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(photo_url, headers=headers, timeout=15)
                
                if response.status_code != 200:
                    print(f"    ⚠️ Ошибка загрузки фото")
                    continue
                
                # Сохраняем временно
                temp_path = f"temp_{int(time.time())}_{i}.jpg"
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                
                # Загружаем на стену VK
                if self.group_id:
                    upload = self.upload.photo_wall(
                        photos=[temp_path],
                        group_id=self.group_id
                    )
                else:
                    upload = self.upload.photo_wall(photos=[temp_path])
                
                # Удаляем временный файл
                try:
                    os.remove(temp_path)
                except:
                    pass
                
                # Добавляем attachment
                photo_id = upload[0]['id']
                owner_id = upload[0]['owner_id']
                photo_attachments.append(f"photo{owner_id}_{photo_id}")
                
                print(f"    ✅ Загружено: photo{owner_id}_{photo_id}")
            
            if not photo_attachments:
                print(f"  ️ Не удалось загрузить ни одного фото")
                return None
            
            # Публикуем пост с фото
            print(f"   Публикуем пост с {len(photo_attachments)} фото...")
            
            attachments_str = ",".join(photo_attachments)
            
            if self.group_id:
                post = self.vk_api.wall.post(
                    owner_id=-int(self.group_id),
                    message=message,
                    attachments=attachments_str,
                    from_group=1
                )
            else:
                post = self.vk_api.wall.post(
                    message=message,
                    attachments=attachments_str
                )
            
            post_id = post['post_id']
            post_owner_id = post['owner_id']
            post_url = f"https://vk.com/wall{post_owner_id}_{post_id}"
            
            print(f"  ✅ Пост создан: {post_url}")
            
            # Получаем URL первого фото для сохранения в базу
            first_photo_url = None
            if photo_attachments:
                # Формируем URL из attachment
                first_photo_url = f"https://sun9-{post_owner_id % 10}.userapi.com/s/v1/ig2/{post_id}.jpg"
            
            return {
                'post_id': post_id,
                'post_url': post_url,
                'photo_url': first_photo_url,
                'attachments': photo_attachments
            }
            
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            return None