import os
import requests
from datetime import datetime

BOT_TOKEN = os.environ.get('BOT_TOKEN')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

print(f"🔗 Подключение к Supabase...")

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
        print(f"  ️ Ошибка получения файла: {e}")
    return None

def extract_phone(text):
    """Извлекаем телефон из текста"""
    import re
    if not text:
        return ''
    phones = re.findall(r'[\+]?[0-9\s\-\(\)]{10,20}', text)
    if phones:
        return phones[0].strip()
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
    """Умная обрезка заголовка до max_length символов без разрыва слов"""
    if not text or len(text) <= max_length:
        return text
    
    # Обрезаем до max_length
    truncated = text[:max_length]
    
    # Ищем последний пробел
    last_space = truncated.rfind(' ')
    
    if last_space > 0:
        truncated = truncated[:last_space]
    
    # Удаляем предлоги и союзы в конце
    stop_words = ['а', 'и', 'в', 'на', 'не', 'при', 'но', 'или', 'если', 'бы', 'ли', 'же', 'то', 'как', 'так', 'для', 'без', 'под', 'над', 'из', 'с', 'к', 'по', 'до', 'от', 'за', 'о', 'об']
    
    words = truncated.split()
    while words and words[-1].lower().strip('.,!?;:') in stop_words:
        words.pop()
    
    return ' '.join(words) if words else text[:max_length]

def get_channel_updates():
    """Основная функция парсера"""
    print("=" * 50)
    print("🚀 Запуск парсера Telegram канала")
    print("=" * 50)
    
    # 1. Получаем last_message_id из Supabase
    print("📥 Получаем последнее состояние парсера...")
    url = f"{SUPABASE_URL}/rest/v1/parser_state?id=eq.1"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"❌ Ошибка чтения parser_state: {response.status_code}")
        return
    
    data = response.json()
    last_id = data[0]['last_message_id'] if data else 0
    
    # 2. Проверяем реальное последнее сообщение в базе ads
    print(" Проверяем последние сообщения в базе ads...")
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
    
    # 4. Проверяем есть ли новые сообщения в Telegram
    print(f"📡 Проверяем обновления в Telegram...")
    telegram_url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates'
    params = {
        'offset': last_id + 1,
        'limit': 1,  # Проверяем только наличие новых
        'timeout': 10
    }
    
    try:
        response = requests.get(telegram_url, params=params, timeout=30)
        data = response.json()
        
        if not data.get('ok'):
            print(f"❌ Telegram API error: {data}")
            return
        
        results = data.get('result', [])
        
        if not results:
            print("ℹ️ Новых сообщений нет. Парсер завершает работу.")
            return
        
        print(f"✅ Найдены новые сообщения! Загружаем...")
        
        # 5. Загружаем все новые сообщения (до 100)
        params['limit'] = 100
        params['offset'] = last_id + 1
        response = requests.get(telegram_url, params=params, timeout=60)
        data = response.json()
        results = data.get('result', [])
        
        print(f"📬 Получено {len(results)} обновлений")
        
        new_ads = []
        max_id = last_id
        saved_count = 0
        
        for update in results:
            print(f"\n🔍 Обрабатываем обновление...")
            
            if 'channel_post' in update:
                post = update['channel_post']
                message_id = post['message_id']
                
                # Пропускаем если уже сохранено
                if message_id <= last_id:
                    print(f"  ⏭️ Уже сохранен (ID: {message_id})")
                    continue
                
                print(f"  📨 Message ID: {message_id}")
                
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
                has_media = False
                
                if 'photo' in post:
                    has_media = True
                    photos = post['photo']
                    if photos:
                        largest_photo = photos[-1]
                        photo_url = get_file_url(largest_photo['file_id'])
                
                if 'video' in post:
                    has_media = True
                    photo_url = get_file_url(post['video']['file_id'])
                
                if 'document' in post:
                    has_media = True
                    photo_url = get_file_url(post['document']['file_id'])
                
                # Создаем объявление
                if text or has_media:
                    title = smart_title(text if text else f"Объявление #{message_id}")
                    description = text if text else "Объявление с медиа файлом"
                    
                    ad = {
                        'tg_message_id': message_id,
                        'title': title,
                        'description': description,
                        'category': parse_category(text) if text else 'другое',
                        'city': parse_city(text) if text else 'Донецк',
                        'phone': extract_phone(text) if text else '',
                        'photo_url': photo_url,
                        'post_link': post_link,
                        'forwarded_from': forwarded_from,
                        'created_at': datetime.now().isoformat()
                    }
                    
                    new_ads.append(ad)
                    max_id = message_id
                    saved_count += 1
                    print(f"  ✅ Добавлено (ID: {message_id})")
        
        print(f"\n📊 Статистика:")
        print(f"  Всего обновлений: {len(results)}")
        print(f"  Новых объявлений: {saved_count}")
        
        # 6. Сохраняем в Supabase
        if new_ads:
            print(f"\n💾 Сохраняем {len(new_ads)} объявлений...")
            url = f"{SUPABASE_URL}/rest/v1/ads"
            headers_upsert = HEADERS.copy()
            headers_upsert["Prefer"] = "resolution=ignore-duplicates,return=representation"
            response = requests.post(url, headers=headers_upsert, json=new_ads)
            
            if response.status_code in [200, 201]:
                print("✅ Объявления сохранены!")
            else:
                print(f"⚠️ Ошибка сохранения: {response.status_code}")
                print(f"Response: {response.text[:200]}")
            
            # 7. Обновляем last_message_id
            print("🔄 Обновляем состояние парсера...")
            url = f"{SUPABASE_URL}/rest/v1/parser_state?id=eq.1"
            update_data = {
                'last_message_id': max_id,
                'updated_at': datetime.now().isoformat()
            }
            response = requests.patch(url, headers=HEADERS, json=update_data)
            
            if response.status_code == 200:
                print(f"\n🎉 Готово! Добавлено {saved_count} объявлений")
                print(f"   last_message_id обновлен: {last_id} → {max_id}")
            else:
                print(f"⚠️ Ошибка обновления состояния: {response.status_code}")
        else:
            print("\n️ Новых объявлений для сохранения нет")
            
    except Exception as e:
        print(f" Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    get_channel_updates()