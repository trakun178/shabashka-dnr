import os
import requests
from datetime import datetime, timezone, timedelta
import json
import time
import sys

# Загружаем переменные из .env файла (если существует)
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    print(f"📁 Загружаем переменные из .env файла...")
    load_dotenv(env_path)
    print(f"   Путь: {env_path}")
else:
    print(f"ℹ️ .env файл не найден, используем GitHub Secrets...")

print(f"\n🔍 Проверка переменных окружения:")
print("=" * 50)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
VK_TOKEN = os.environ.get('VK_TOKEN', '')
VK_GROUP_ID = os.environ.get('VK_GROUP_ID', '')

print(f"  BOT_TOKEN: {'✅ Установлен' if BOT_TOKEN else '❌ НЕ установлен'}")
print(f"  SUPABASE_URL: {'✅ Установлен' if SUPABASE_URL else '❌ НЕ установлен'}")
print(f"  SUPABASE_KEY: {'✅ Установлен' if SUPABASE_KEY else '❌ НЕ установлен'}")
print(f"  VK_TOKEN: {'✅ Установлен' if VK_TOKEN else '❌ НЕ установлен'}")
print(f"  VK_GROUP_ID: {'✅ Установлен' if VK_GROUP_ID else '❌ НЕ установлен'}")

if VK_TOKEN:
    print(f"  VK_TOKEN (первые 20 симв): {VK_TOKEN[:20]}...")
if VK_GROUP_ID:
    print(f"  VK_GROUP_ID: {VK_GROUP_ID}")

print("=" * 50)

# Инициализация VK uploader
vk_uploader = None
if VK_TOKEN and VK_GROUP_ID:
    try:
        from vk_uploader import VKUploader
        vk_uploader = VKUploader(VK_TOKEN, VK_GROUP_ID)
        print(f"✅ VK uploader инициализирован (группа: {VK_GROUP_ID})")
    except Exception as e:
        print(f"❌ Ошибка инициализации VK: {e}")
        import traceback
        traceback.print_exc()
        vk_uploader = None
elif VK_TOKEN:
    print(f"️ VK_TOKEN есть, но VK_GROUP_ID НЕ установлен - VK отключён")
else:
    print(f"⚠️ VK_TOKEN НЕ установлен - VK отключён")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL или SUPABASE_KEY не установлены!")
    exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def get_file_url(file_id):
    """Получаем URL файла по file_id"""
    try:
        file_url = f'https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}'
        file_response = requests.get(file_url)
        file_data = file_response.json()
        
        if file_data.get('ok'):
            file_path = file_data['result']['file_path']
            return f'https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}'
    except Exception as e:
        print(f"  ⚠️ Ошибка получения файла: {e}")
    return None

def extract_phone(text):
    """Извлекаем телефон из текста - только цифры"""
    import re
    if not text:
        return ''
    # Ищем только цифры и + в начале, 10-15 цифр
    phones = re.findall(r'\+?\d{10,15}', text)
    if phones:
        return phones[0]
    return ''

def parse_category(text):
    """Определяем категорию объявления"""
    if not text:
        return 'другое'
    
    text_lower = text.lower()
    categories = {
        'ремонт': ['ремонт', 'отделка', 'плитка', 'поклейка', 'покраска'],
        'сантехника': ['сантехник', 'вода', 'канализация', 'трубы', 'унитаз'],
        'электрика': ['электрик', 'проводка', 'розетка', 'свет', 'электр'],
        'строительство': ['строитель', 'кладка', 'бетон', 'фундамент'],
        'грузчики': ['грузчик', 'вывоз', 'переезд', 'разгрузка'],
        'уборка': ['уборка', 'клининг', 'мойка'],
        'окна': ['окон', 'окна', 'оконный', 'москитн'],
    }
    
    for category, keywords in categories.items():
        if any(kw in text_lower for kw in keywords):
            return category
    
    return 'другое'

def parse_city(text):
    """Определяем город"""
    if not text:
        return 'Донецк'
    
    text_lower = text.lower()
    if 'донецк' in text_lower:
        return 'Донецк'
    elif 'макеевка' in text_lower:
        return 'Макеевка'
    elif 'горловка' in text_lower:
        return 'Горловка'
    
    return 'Донецк'

def smart_title(text, max_length=70):
    """Умная обрезка заголовка"""
    if not text or len(text) <= max_length:
        return text
    
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > 0:
        truncated = truncated[:last_space]
    
    stop_words = ['а', 'и', 'в', 'на', 'не', 'при', 'но', 'или', 'если', 'бы', 'ли', 'же', 'то', 'как', 'так', 'для', 'без', 'под', 'над', 'из', 'с', 'к', 'по', 'до', 'от', 'за', 'о', 'об']
    
    words = truncated.split()
    while words and words[-1].lower().strip('.,!?;:') in stop_words:
        words.pop()
    
    return ' '.join(words) if words else text[:max_length]

def get_channel_updates():
    """Основная функция парсера"""
    print("\n" + "=" * 50)
    print(" Запуск парсера Telegram канала")
    print("=" * 50)
    
    # 1. Получаем last_message_id из Supabase
    print("📥 Получаем последнее состояние парсера...")
    url = f"{SUPABASE_URL}/rest/v1/parser_state?id=eq.1"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"❌ Ошибка чтения parser_state: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return
    
    data = response.json()
    last_id = data[0]['last_message_id'] if data else 0
    
    # 2. Проверяем реальное последнее сообщение в базе ads
    print("🔍 Проверяем последние сообщения в базе ads...")
    ads_url = f"{SUPABASE_URL}/rest/v1/ads?order=tg_message_id.desc&limit=1"
    ads_response = requests.get(ads_url, headers=HEADERS)
    
    real_last_id = 0
    if ads_response.status_code == 200:
        ads_data = ads_response.json()
        if ads_data and len(ads_data) > 0:
            real_last_id = ads_data[0]['tg_message_id']
            print(f"✅ Последнее сообщение в ads: {real_last_id}")
    
    # 3. Используем МАКСИМАЛЬНОЕ значение
    if real_last_id > last_id:
        print(f"⚠️ last_message_id устарел! Используем {real_last_id} вместо {last_id}")
        last_id = real_last_id
    
    print(f"✅ Будем искать сообщения > {last_id}")
    
    # 4. Получаем ВСЕ доступные обновления из Telegram
    print(f"\n📡 Получаем обновления из Telegram...")
    telegram_url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates'
    params = {
        'limit': 100,
        'timeout': 30,
        'offset': last_id + 1
    }
    
    # Пробуем подключиться 3 раза
    max_retries = 3
    data = None
    
    for attempt in range(max_retries):
        try:
            print(f"  Попытка {attempt + 1} из {max_retries}...")
            
            response = requests.get(
                telegram_url, 
                params=params, 
                timeout=60,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    print(f"  ✅ Подключение к Telegram успешно!")
                    break
                else:
                    print(f"  ❌ Telegram API error: {data}")
                    return
            else:
                print(f"  ⚠️ Ошибка {response.status_code}: {response.text[:100]}")
                if attempt < max_retries - 1:
                    print(f"   Ждём 10 секунд перед повторной попыткой...")
                    time.sleep(10)
                    
        except requests.exceptions.ConnectTimeout:
            print(f"  ⏱️ Таймаут подключения (попытка {attempt + 1})")
            if attempt < max_retries - 1:
                print(f"   Ждём 15 секунд...")
                time.sleep(15)
            continue
            
        except requests.exceptions.ConnectionError as e:
            print(f"  ❌ Ошибка подключения: {str(e)[:100]}")
            print(f"\n💡 Возможные причины:")
            print(f"   1. Telegram заблокирован - нужен VPN/прокси")
            print(f"   2. Проблемы с интернетом")
            print(f"   3. Неправильный BOT_TOKEN")
            if attempt < max_retries - 1:
                print(f"   Повторная попытка через 10 секунд...")
                time.sleep(10)
            continue
            
        except Exception as e:
            print(f"  Неожиданная ошибка: {e}")
            if attempt < max_retries - 1:
                time.sleep(10)
            continue
    
    if data is None or not data.get('ok'):
        print(f"\n❌ Не удалось подключиться к Telegram после {max_retries} попыток")
        return
    
    all_updates = data.get('result', [])
    print(f"📩 Получено {len(all_updates)} обновлений из Telegram")
    
    # 5. Фильтруем ТОЛЬКО channel_post с message_id > last_id
    results = []
    for update in all_updates:
        if 'channel_post' in update:
            message_id = update['channel_post']['message_id']
            if message_id > last_id:
                results.append(update)
                print(f"  ✅ Новое сообщение: {message_id}")
            else:
                print(f"  ⏭️ Пропущено (старое): {message_id}")
    
    if not results:
        print("\nℹ️ Новых сообщений нет. Парсер завершает работу.")
        return
    
    print(f"\n✅ Найдено {len(results)} новых сообщений для обработки")
    
    # 6. ГРУППИРУЕМ сообщения по media_group_id
    print("\n Группируем сообщения по альбомам...")
    groups = {}  # media_group_id -> список сообщений
    single_messages = []  # сообщения без media_group_id
    
    for update in results:
        post = update['channel_post']
        media_group_id = post.get('media_group_id')
        
        if media_group_id:
            if media_group_id not in groups:
                groups[media_group_id] = []
            groups[media_group_id].append(post)
            print(f"  📸 Сообщение {post['message_id']} в альбоме {media_group_id}")
        else:
            single_messages.append(post)
            print(f"  📝 Одиночное сообщение {post['message_id']}")
    
    print(f"\n📊 Статистика группировки:")
    print(f"  Альбомов: {len(groups)}")
    print(f"  Одиночных сообщений: {len(single_messages)}")
    
    # 7. Обрабатываем альбомы (группы фото)
    new_ads = []
    max_id = last_id
    saved_count = 0
    vk_posts_count = 0
    
    for media_group_id, posts in groups.items():
        print(f"\n🔄 Обрабатываем альбом {media_group_id} ({len(posts)} фото)...")
        
        # Берём первое сообщение как основное
        main_post = posts[0]
        message_id = main_post['message_id']
        
        # Получаем время создания поста (из Telegram)
        tg_date = datetime.fromtimestamp(main_post['date'], tz=timezone.utc)
        msk_tz = timezone(timedelta(hours=3))
        created_at_msk = tg_date.astimezone(msk_tz)
        
        # Собираем текст из всех сообщений группы
        combined_text = ''
        for post in posts:
            text = post.get('text', '')
            if not text and 'caption' in post:
                text = post['caption']
            if text:
                combined_text += text + '\n'
        
        combined_text = combined_text.strip()
        
        # Собираем ВСЕ фото из альбома
        photo_urls = []
        for post in posts:
            if 'photo' in post:
                photos = post['photo']
                if photos:
                    largest_photo = photos[-1]
                    photo_url = get_file_url(largest_photo['file_id'])
                    if photo_url:
                        photo_urls.append(photo_url)
            elif 'video' in post:
                photo_url = get_file_url(post['video']['file_id'])
                if photo_url:
                    photo_urls.append(photo_url)
            elif 'document' in post:
                photo_url = get_file_url(post['document']['file_id'])
                if photo_url:
                    photo_urls.append(photo_url)
        
        print(f"  📸 Найдено фото: {len(photo_urls)}")
        
        # Публикуем в VK (если есть uploader и есть текст или фото)
        vk_result = None
        
        if vk_uploader and (combined_text or photo_urls):
            print(f"  📤 Публикуем пост в VK...")
            
            # Ссылка на пост в Telegram
            post_link = f"https://t.me/{main_post.get('chat', {}).get('username', 'dnrsabbath')}/{message_id}"
            
            # Переслано от
            forwarded_from = main_post.get('forward_sender_name') or \
                            (main_post.get('forward_from_chat', {}).get('title') if 'forward_from_chat' in main_post else None)
            
            # Формируем текст для VK
            vk_message = combined_text[:4096] if len(combined_text) > 4096 else combined_text
            
            # Публикуем пост
            vk_result = vk_uploader.post_with_photos(
                message=vk_message,
                photo_urls=photo_urls if photo_urls else None,
                forwarded_from=forwarded_from,
                post_link=post_link
            )
            
            if vk_result:
                vk_posts_count += 1
                print(f"  ✅ Пост в VK: {vk_result['post_url']}")

            # Делаем задержку ТОЛЬКО если это не последнее сообщение
            current_group_index = list(groups.keys()).index(media_group_id)
            if current_group_index < len(groups) - 1 or single_messages:
                print("  ⏱️ Ожидание 65 секунд перед следующим постом...")
                time.sleep(65)
        
        # Создаём объявление
        if combined_text or photo_urls:
            title = smart_title(combined_text if combined_text else f"Объявление #{message_id}")
            description = combined_text if combined_text else "Объявление с медиа файлом"
            
            # Используем данные из VK
            vk_post_url = vk_result['post_url'] if vk_result else None
            
            # ✅ ИСПРАВЛЕНИЕ: Берем ВЕСЬ массив фото из VK, если загрузка прошла успешно
            if vk_result and vk_result.get('photo_urls'):
                final_photo_urls = vk_result['photo_urls']
            else:
                final_photo_urls = photo_urls if photo_urls else []
                
            final_photo_url = final_photo_urls[0] if final_photo_urls else None
            
            # Ссылка на пост в Telegram
            post_link = f"https://t.me/{main_post.get('chat', {}).get('username', 'dnrsabbath')}/{message_id}"
            
            # Переслано от
            forwarded_from = main_post.get('forward_sender_name') or \
                            (main_post.get('forward_from_chat', {}).get('title') if 'forward_from_chat' in main_post else None)
            
            ad = {
                'tg_message_id': message_id,
                'title': title,
                'description': description,
                'category': parse_category(combined_text) if combined_text else 'другое',
                'city': parse_city(combined_text) if combined_text else 'Донецк',
                'phone': extract_phone(combined_text) if combined_text else '',
                'photo_url': final_photo_url,
                'photo_urls': json.dumps(final_photo_urls),
                'vk_post_url': vk_post_url,
                'post_link': post_link,
                'forwarded_from': forwarded_from,
                'created_at': created_at_msk.isoformat()
            }
            
            new_ads.append(ad)
            max_id = max(max_id, message_id)
            saved_count += 1
            print(f"  ✅ Альбом добавлен (ID: {message_id}, фото: {len(final_photo_urls)})")
    
    # 8. Обрабатываем одиночные сообщения
    for post in single_messages:
        print(f"\n Обрабатываем одиночное сообщение...")
        
        message_id = post['message_id']
        
        # Получаем время создания поста (из Telegram)
        tg_date = datetime.fromtimestamp(post['date'], tz=timezone.utc)
        msk_tz = timezone(timedelta(hours=3))
        created_at_msk = tg_date.astimezone(msk_tz)
        
        # Получаем текст
        text = post.get('text', '')
        if not text and 'caption' in post:
            text = post['caption']
        
        # Ссылка на пост
        channel_username = post.get('chat', {}).get('username', 'dnrsabbath')
        post_link = f"https://t.me/{channel_username}/{message_id}"
        
        # Переслано от
        forwarded_from = None
        if 'forward_from' in post:
            sender = post['forward_from']
            forwarded_from = sender.get('first_name', '') + ' ' + sender.get('last_name', '')
            if sender.get('username'):
                forwarded_from += f" (@{sender['username']})"
        elif 'forward_from_chat' in post:
            chat = post['forward_from_chat']
            forwarded_from = chat.get('title', 'Unknown')
            if chat.get('username'):
                forwarded_from += f" (@{chat['username']})"
        elif 'forward_sender_name' in post:
            forwarded_from = post['forward_sender_name']
            if not forwarded_from or not any(c.isalpha() for c in forwarded_from):
                forwarded_from = "Скрытый профиль"
        
        # Медиа
        photo_url = None
        photo_urls = []
        has_media = False
        
        if 'photo' in post:
            has_media = True
            photos = post['photo']
            if photos:
                largest_photo = photos[-1]
                photo_url = get_file_url(largest_photo['file_id'])
                if photo_url:
                    photo_urls.append(photo_url)
        
        if 'video' in post:
            has_media = True
            photo_url = get_file_url(post['video']['file_id'])
            if photo_url:
                photo_urls.append(photo_url)
        
        if 'document' in post:
            has_media = True
            photo_url = get_file_url(post['document']['file_id'])
            if photo_url:
                photo_urls.append(photo_url)
        
        # Публикуем в VK (если есть uploader и есть текст или фото)
        vk_result = None
        
        if vk_uploader and (text or photo_urls):
            print(f"   Публикуем пост в VK...")
            
            # Формируем текст для VK
            vk_message = text[:4096] if len(text) > 4096 else text
            
            # Публикуем пост
            vk_result = vk_uploader.post_with_photos(
                message=vk_message,
                photo_urls=photo_urls if photo_urls else None,
                forwarded_from=forwarded_from,
                post_link=post_link
            )
            
            if vk_result:
                vk_posts_count += 1
                print(f"  ✅ Пост в VK: {vk_result['post_url']}")

            # Делаем задержку ТОЛЬКО если это не последнее сообщение
            current_msg_index = single_messages.index(post)
            if current_msg_index < len(single_messages) - 1:
                print("  ⏱️ Ожидание 65 секунд перед следующим постом...")
                time.sleep(65)
        
        # Создаем объявление
        if text or has_media:
            title = smart_title(text if text else f"Объявление #{message_id}")
            description = text if text else "Объявление с медиа файлом"
            
            # Используем данные из VK
            vk_post_url = vk_result['post_url'] if vk_result else None
            
            # ✅ ИСПРАВЛЕНИЕ: Берем ВЕСЬ массив фото из VK, если загрузка прошла успешно
            if vk_result and vk_result.get('photo_urls'):
                final_photo_urls = vk_result['photo_urls']
            else:
                final_photo_urls = photo_urls if photo_urls else []
                
            final_photo_url = final_photo_urls[0] if final_photo_urls else None
            
            ad = {
                'tg_message_id': message_id,
                'title': title,
                'description': description,
                'category': parse_category(text) if text else 'другое',
                'city': parse_city(text) if text else 'Донецк',
                'phone': extract_phone(text) if text else '',
                'photo_url': final_photo_url,
                'photo_urls': json.dumps(final_photo_urls),
                'vk_post_url': vk_post_url,
                'post_link': post_link,
                'forwarded_from': forwarded_from,
                'created_at': created_at_msk.isoformat()
            }
            
            new_ads.append(ad)
            max_id = max(max_id, message_id)
            saved_count += 1
            print(f"  ✅ Добавлено (ID: {message_id})")
    
    print(f"\n📊 Итоговая статистика:")
    print(f"  Всего обновлений: {len(results)}")
    print(f"  Альбомов: {len(groups)}")
    print(f"  Одиночных: {len(single_messages)}")
    print(f"  Новых объявлений: {saved_count}")
    print(f"  Постов в VK: {vk_posts_count}")
    
    # 9. Сохраняем в Supabase
    if new_ads:
        print(f"\n💾 Сохраняем {len(new_ads)} объявлений...")
        url = f"{SUPABASE_URL}/rest/v1/ads"
        headers_upsert = HEADERS.copy()
        headers_upsert["Prefer"] = "resolution=ignore-duplicates,return=representation"
        response = requests.post(url, headers=headers_upsert, json=new_ads)
        
        if response.status_code in [200, 201]:
            print("✅ Объявления успешно сохранены в базу!")
            
            # ✅ 10. Обновляем last_message_id ТОЛЬКО ПРИ УСПЕШНОМ СОХРАНЕНИИ
            print("🔄 Обновляем состояние парсера...")
            url_state = f"{SUPABASE_URL}/rest/v1/parser_state?id=eq.1"
            update_data = {
                'last_message_id': max_id,
                'updated_at': datetime.now(msk_tz).isoformat()
            }
            state_response = requests.patch(url_state, headers=HEADERS, json=update_data)
            
            if state_response.status_code == 200:
                print(f"✅ Готово! last_message_id обновлен: {last_id} → {max_id}")
            else:
                print(f"⚠️ Ошибка обновления состояния: {state_response.status_code}")
        else:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Объявления НЕ сохранены (Код: {response.status_code})")
            print(f"Ответ Supabase: {response.text[:300]}")
            print("⚠️ last_message_id НЕ обновлен! При следующем запуске парсер попробует сохранить их снова.")
    else:
        print("\nℹ️ Новых объявлений для сохранения нет")

if __name__ == '__main__':
    get_channel_updates()