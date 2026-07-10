import os
import requests
from datetime import datetime

BOT_TOKEN = os.environ.get('BOT_TOKEN')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

print(f"🔗 Подключение к Supabase...")
print(f"URL: {SUPABASE_URL}")
print(f"Key length: {len(SUPABASE_KEY) if SUPABASE_KEY else 0}")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL или SUPABASE_KEY не установлены!")
    exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def test_connection():
    try:
        url = f"{SUPABASE_URL}/rest/v1/parser_state"
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            print("✅ Успешно подключились к Supabase!")
            return True
        else:
            print(f" Ошибка подключения: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

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

def get_channel_updates():
    print("📥 Получаем последнее состояние парсера...")
    
    url = f"{SUPABASE_URL}/rest/v1/parser_state?id=eq.1"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"❌ Ошибка чтения parser_state: {response.status_code}")
        return
    
    data = response.json()
    last_id = data[0]['last_message_id'] if data else 0
    print(f"Последний message_id: {last_id}")
    
    print(f"📡 Запрашиваем обновления из канала...")
    telegram_url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates'
    params = {
        'offset': last_id + 1,
        'limit': 100,
        'timeout': 10
    }
    
    try:
        response = requests.get(telegram_url, params=params, timeout=60)
        data = response.json()
        
        if not data.get('ok'):
            print(f"❌ Telegram API error: {data}")
            return
        
        results = data.get('result', [])
        print(f"📬 Получено {len(results)} обновлений")
        
        new_ads = []
        max_id = last_id
        skipped_count = 0
        
        for update in results:
            print(f"\n🔍 Обрабатываем обновление...")
            
            if 'channel_post' in update:
                post = update['channel_post']
                message_id = post['message_id']
                
                print(f"  📨 Message ID: {message_id}")
                
                # Получаем текст
                text = post.get('text', '')
                
                # Если текста нет, пробуем взять caption
                if not text and 'caption' in post:
                    text = post['caption']
                    print(f"  📝 Взято из caption (длина: {len(text)})")
                
                # Ссылка на пост в канале
                channel_username = post.get('chat', {}).get('username', 'dnrsabbath')
                post_link = f"https://t.me/{channel_username}/{message_id}"
                print(f"  🔗 Ссылка: {post_link}")
                
                # Переслано от
                forwarded_from = None
                if 'forward_from' in post:
                    sender = post['forward_from']
                    forwarded_from = sender.get('first_name', '') + ' ' + sender.get('last_name', '')
                    if sender.get('username'):
                        forwarded_from += f" (@{sender['username']})"
                    print(f"  ↪️ Переслано от: {forwarded_from.strip()}")
                elif 'forward_from_chat' in post:
                    chat = post['forward_from_chat']
                    forwarded_from = chat.get('title', 'Unknown')
                    if chat.get('username'):
                        forwarded_from += f" (@{chat['username']})"
                    print(f"  ↪️ Переслано из канала: {forwarded_from}")
                elif 'forward_sender_name' in post:
                    forwarded_from = post['forward_sender_name']
                    # Если это эмодзи или пустая строка
                    if not forwarded_from or not any(c.isalpha() for c in forwarded_from):
                        forwarded_from = "Скрытый профиль"
                    print(f"  ↪️ Переслано от: {forwarded_from}")
                
                # Собираем медиа - ТОЛЬКО ОДНО САМОЕ БОЛЬШОЕ ФОТО
                photo_url = None
                has_media = False
                
                # Фото - берем только последнее (самое большое разрешение)
                if 'photo' in post:
                    has_media = True
                    photos = post['photo']
                    print(f"  📷 Фото: {len(photos)} разрешений")
                    
                    if photos:
                        largest_photo = photos[-1]
                        file_id = largest_photo['file_id']
                        photo_url = get_file_url(file_id)
                        if photo_url:
                            print(f"  📷 Фото URL (max): {photo_url[:60]}...")
                
                # Видео
                if 'video' in post:
                    has_media = True
                    video = post['video']
                    file_id = video['file_id']
                    photo_url = get_file_url(file_id)
                    if photo_url:
                        print(f"   Видео: {photo_url[:60]}...")
                
                # Документ
                if 'document' in post:
                    has_media = True
                    doc = post['document']
                    file_id = doc['file_id']
                    photo_url = get_file_url(file_id)
                    if photo_url:
                        print(f"  📄 Документ: {photo_url[:60]}...")
                
                # Если есть текст ИЛИ медиа - сохраняем
                if text or has_media:
                    title = text[:100] if text else f"Объявление #{message_id}"
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
                    print(f"  ✅ Добавлено объявление #{message_id}")
                    print(f"     Текст: {len(text)} символов, Медиа: {'есть' if photo_url else 'нет'}")
                    if forwarded_from:
                        print(f"     Переслано от: {forwarded_from}")
                else:
                    print(f"  ⚠️ Пропущено: нет текста и медиа")
                    skipped_count += 1
                    if message_id > max_id:
                        max_id = message_id
            else:
                print(f"  ⚠️ Пропущено (не channel_post)")
                skipped_count += 1
        
        print(f"\n📊 Статистика:")
        print(f"  Всего обновлений: {len(results)}")
        print(f"  Новых объявлений: {len(new_ads)}")
        print(f"  Пропущено: {skipped_count}")
        
        if new_ads:
            print(f"\n💾 Сохраняем {len(new_ads)} объявлений...")
            # Используем upsert с игнорированием дубликатов
            url = f"{SUPABASE_URL}/rest/v1/ads"
            headers_upsert = HEADERS.copy()
            headers_upsert["Prefer"] = "resolution=ignore-duplicates,return=representation"
            response = requests.post(url, headers=headers_upsert, json=new_ads)
            
            if response.status_code in [200, 201]:
                print("✅ Объявления сохранены!")
            else:
                print(f"❌ Ошибка сохранения: {response.status_code}")
                print(f"Response: {response.text}")
            
            print("🔄 Обновляем состояние парсера...")
            url = f"{SUPABASE_URL}/rest/v1/parser_state?id=eq.1"
            update_data = {
                'last_message_id': max_id,
                'updated_at': datetime.now().isoformat()
            }
            response = requests.patch(url, headers=HEADERS, json=update_data)
            
            if response.status_code == 200:
                print(f"\n🎉 Готово! Добавлено {len(new_ads)} объявлений")
            else:
                print(f"⚠️ Ошибка обновления состояния: {response.status_code}")
        else:
            print("\nℹ️ Новых объявлений нет")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

def extract_phone(text):
    import re
    if not text:
        return ''
    phones = re.findall(r'[\+]?[0-9\s\-\(\)]{10,20}', text)
    if phones:
        return phones[0].strip()
    return ''

def parse_category(text):
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

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Запуск парсера Telegram канала")
    print("=" * 50)
    
    if not test_connection():
        exit(1)
    
    get_channel_updates()