import requests
import time
import os

class VKUploader:
    def __init__(self, token, group_id=None):
        self.token = token
        self.group_id = group_id
        self.api_url = "https://api.vk.com/method"
        print(f"✅ VK uploader инициализирован (группа: {group_id})")
    
    def _api_call(self, method, params=None):
        """Прямой вызов API VK"""
        if params is None:
            params = {}
        
        params['access_token'] = self.token
        params['v'] = '5.131'  # Версия API
        
        url = f"{self.api_url}/{method}"
        response = requests.post(url, data=params)
        data = response.json()
        
        if 'error' in data:
            error = data['error']
            print(f"    ❌ VK API Error {error.get('error_code')}: {error.get('error_msg')}")
            return None
        
        return data.get('response')
    
    def post_with_photos(self, message, photo_urls):
        """Загружаем фото и публикуем пост через прямые HTTP запросы"""
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
                    print(f"    ️ Ошибка скачивания: {response.status_code}")
                    continue
                
                # Сохраняем временно
                temp_path = f"temp_{int(time.time())}_{i}.jpg"
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                
                # Загружаем фото через API
                try:
                    # 1. Получаем URL для загрузки
                    upload_server = self._api_call('photos.getWallUploadServer', {
                        'group_id': self.group_id
                    })
                    
                    if not upload_server:
                        print(f"    ❌ Не получен upload_server")
                        continue
                    
                    upload_url = upload_server['upload_url']
                    
                    # 2. Загружаем файл
                    with open(temp_path, 'rb') as f:
                        upload_response = requests.post(
                            upload_url,
                            files={'photo': f}
                        ).json()
                    
                    if 'photo' not in upload_response:
                        print(f"    ❌ Ошибка загрузки файла")
                        continue
                    
                    # 3. Сохраняем фото
                    saved = self._api_call('photos.saveWallPhoto', {
                        'photo': upload_response['photo'],
                        'hash': upload_response.get('hash', ''),
                        'server': upload_response.get('server', 0)
                    })
                    
                    if saved and len(saved) > 0:
                        photo_id = saved[0]['id']
                        photo_attachments.append(f"photo{group_owner_id}_{photo_id}")
                        print(f"    ✅ Загружено: photo{group_owner_id}_{photo_id}")
                    else:
                        print(f"    ❌ Не удалось сохранить фото")
                    
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
            print(f"  📝 Публикуем пост с {len(photo_attachments)} фото...")
            
            attachments_str = ",".join(photo_attachments)
            
            # Публикуем пост через API
            post = self._api_call('wall.post', {
                'owner_id': group_owner_id,
                'message': message[:4096],
                'attachments': attachments_str,
                'from_group': 1
            })
            
            if post:
                post_id = post['post_id']
                post_url = f"https://vk.com/wall{group_owner_id}_{post_id}"
                print(f"  ✅ Пост создан: {post_url}")
                
                return {
                    'post_id': post_id,
                    'post_url': post_url,
                    'photo_url': None,
                    'attachments': photo_attachments
                }
            else:
                print(f"  ❌ Не удалось создать пост")
                return None
            
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            return None