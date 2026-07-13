import requests
import vk_api
from vk_api.upload import VkUpload
import time

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
    
    def upload_photo_from_url(self, photo_url, album_id=None):
        """Загружаем фото по URL в VK"""
        try:
            # Скачиваем фото
            response = requests.get(photo_url, timeout=10)
            if response.status_code != 200:
                print(f"  ⚠️ Ошибка загрузки фото: {response.status_code}")
                return None
            
            # Сохраняем временно
            temp_path = f"temp_{int(time.time())}.jpg"
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            # Загружаем в VK
            if album_id:
                # В альбом
                upload = self.upload.photo(album_id=album_id, photos=[temp_path])
            else:
                # На стену (без альбома)
                if self.group_id:
                    upload = self.upload.photo_group_wall(
                        group_id=self.group_id,
                        photos=[temp_path]
                    )
                else:
                    upload = self.upload.photo_wall(photos=[temp_path])
            
            # Удаляем временный файл
            import os
            os.remove(temp_path)
            
            # Получаем URL фото
            photo_id = upload[0]['id']
            owner_id = upload[0]['owner_id']
            
            # Формируем URL для отображения
            photo_url_vk = f"https://sun9-{owner_id % 10}.userapi.com/s/v1/ig2/{photo_id}.jpg"
            
            print(f"  ✅ Фото загружено в VK: {photo_url_vk}")
            return {
                'id': photo_id,
                'owner_id': owner_id,
                'url': photo_url_vk,
                'attachment': f"photo{owner_id}_{photo_id}"
            }
            
        except Exception as e:
            print(f"  ❌ Ошибка загрузки фото в VK: {e}")
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
            
            # Публикуем пост
            if self.group_id:
                # В группу
                post = self.vk_api.wall.post(
                    owner_id=-int(self.group_id),  # Минус для группы
                    message=message,
                    attachments=attachments_str,
                    link=link
                )
            else:
                # На личную страницу
                post = self.vk_api.wall.post(
                    message=message,
                    attachments=attachments_str,
                    link=link
                )
            
            post_id = post['post_id']
            post_url = f"https://vk.com/wall-{self.group_id}_{post_id}" if self.group_id else f"https://vk.com/wall{post['owner_id']}_{post_id}"
            
            print(f"  ✅ Пост создан: {post_url}")
            return {
                'id': post_id,
                'url': post_url
            }
            
        except Exception as e:
            print(f"  ❌ Ошибка создания поста: {e}")
            return None