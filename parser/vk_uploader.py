import requests
import vk_api
from vk_api.upload import VkUpload
import time
import os

class VKUploader:
    def __init__(self, token, group_id=None):
        """
        token: VK access token
        group_id: ID группы (без минуса, например "123456789")
        """
        self.vk = vk_api.VkApi(token=token)
        self.upload = VkUpload(self.vk)
        self.group_id = group_id
        self.vk_api = self.vk.get_api()
        print(f"✅ VK uploader инициализирован (группа: {group_id})")
    
    def upload_photo_from_url(self, photo_url, album_id=None):
        """Загружаем фото по URL в VK"""
        try:
            print(f"  📥 Скачиваем фото: {photo_url[:50]}...")
            
            # Скачиваем фото
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(photo_url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                print(f"  ️ Ошибка загрузки фото: {response.status_code}")
                return None
            
            # Сохраняем временно
            temp_path = f"temp_{int(time.time())}.jpg"
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            print(f"  📤 Загружаем в VK...")
            
            # Загружаем в VK
            if self.group_id:
                # В группу
                upload = self.upload.photo_group_wall(
                    group_id=self.group_id,
                    photos=[temp_path]
                )
            else:
                # На личную страницу
                upload = self.upload.photo_wall(photos=[temp_path])
            
            # Удаляем временный файл
            try:
                os.remove(temp_path)
            except:
                pass
            
            # Получаем данные фото
            photo_id = upload[0]['id']
            owner_id = upload[0]['owner_id']
            
            # Получаем URL фото из VK
            # Формируем правильный URL для отображения
            photo_sizes = upload[0].get('sizes', [])
            if photo_sizes:
                # Берём самое большое фото
                largest = max(photo_sizes, key=lambda x: x.get('width', 0))
                photo_url_vk = largest['url']
            else:
                # Фallback - формируем URL
                photo_url_vk = f"https://sun9-{owner_id % 10}.userapi.com/s/v1/ig2/{photo_id}.jpg"
            
            print(f"  ✅ Фото загружено в VK: {photo_url_vk[:60]}...")
            
            return {
                'id': photo_id,
                'owner_id': owner_id,
                'url': photo_url_vk,
                'attachment': f"photo{owner_id}_{photo_id}"
            }
            
        except Exception as e:
            print(f"  ❌ Ошибка загрузки фото в VK: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_post(self, message, photo_attachments=None, link=None):
        """Создаём пост в VK"""
        try:
            attachments = []
            
            # Добавляем фото
            if photo_attachments:
                for photo in photo_attachments:
                    if photo and 'attachment' in photo:
                        attachments.append(photo['attachment'])
            
            attachments_str = ",".join(attachments) if attachments else ""
            
            print(f"  📝 Публикуем пост в VK...")
            print(f"  Текст: {message[:100]}...")
            print(f"  Вложений: {len(attachments)}")
            
            # Публикуем пост
            if self.group_id:
                # В группу (отрицательный ID)
                post = self.vk_api.wall.post(
                    owner_id=-int(self.group_id),
                    message=message,
                    attachments=attachments_str,
                    from_group=1  # Публикуем от имени группы
                )
            else:
                # На личную страницу
                post = self.vk_api.wall.post(
                    message=message,
                    attachments=attachments_str
                )
            
            post_id = post['post_id']
            post_owner_id = post['owner_id']
            post_url = f"https://vk.com/wall{post_owner_id}_{post_id}"
            
            print(f"  ✅ Пост создан: {post_url}")
            
            return {
                'id': post_id,
                'owner_id': post_owner_id,
                'url': post_url
            }
            
        except Exception as e:
            print(f"  ❌ Ошибка создания поста: {e}")
            import traceback
            traceback.print_exc()
            return None