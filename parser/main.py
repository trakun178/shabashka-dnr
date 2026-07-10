import os
import requests
from datetime import datetime

# Telegram Bot
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL = '@dnrsabbath'

# Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

print(f"🔗 Подключение к Supabase...")
print(f"URL: {SUPABASE_URL}")
print(f"Key length: {len(SUPABASE_KEY) if SUPABASE_KEY else 0}")
print(f"Key starts with: {SUPABASE_KEY[:20] if SUPABASE_KEY else 'None'}...")

# Проверяем что ключи есть
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL или SUPABASE_KEY не установлены!")
    exit(1)

# Используем REST API напрямую вместо библиотеки supabase
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def test_connection():
    """Тестируем подключение к Supabase"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/parser_state"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            print("✅ Успешно подключились к Supabase!")
            return True
        else:
            print(f"❌ Ошибка подключения: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def get_channel_updates():
    """Получаем новые сообщения из канала"""
    
    print("📥 Получаем последнее состояние парсера...")
    
    # Получаем последний ID из базы
    url = f"{SUPABASE_URL}/rest/v1/parser_state?id=eq.1"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"❌ Ошибка чтения parser_state: {response.status_code}")
        print(f"Response: {response.text}")
        return
    
    data = response.json()
    last_id = data[0]['last_message_id'] if data else 0
    print(f"Последний message_id: {last_id}")
    
    # Запрашиваем обновления через Bot API
    print(f"📨 Запрашиваем обновления из канала...")
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
            print(f" Telegram API error: {data}")
            return
        
        results = data.get('result', [])
        print(f"📬 Получено {len(results)} обновлений")
        
        new_ads = []
        max_id = last_id
        
        for update in results:
            if 'channel_post' in update:
                post = update['channel_post']
                message_id = post['message_id']
                
                if message_id > last_id:
                    text = post.get('text', '')
                    
                    if text:
                        ad = {
                            'tg_message_id': message_id,
                            'title': text[:100] if len(text) > 100 else text,
                            'description': text,
                            'category': parse_category(text),
                            'city': parse_city(text),
                            'phone': extract_phone(text),
                            'photo_url': None,
                            'created_at': datetime.now().isoformat()
                        }
                        
                        new_ads.append(ad)
                        max_id = message_id
                        print(f"  ✓ Добавлено объявление #{message_id}")
        
        # Сохраняем в базу
        if new_ads:
            print(f"\n💾 Сохраняем {len(new_ads)} объявлений...")
            url = f"{SUPABASE_URL}/rest/v1/ads"
            response = requests.post(url, headers=HEADERS, json=new_ads)
            
            if response.status_code in [200, 201]:
                print("✅ Объявления сохранены!")
            else:
                print(f"❌ Ошибка сохранения: {response.status_code}")
                print(f"Response: {response.text}")
            
            # Обновляем состояние
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
                print(f"❌ Ошибка обновления состояния: {response.status_code}")
        else:
            print("\nℹ️ Новых объявлений нет")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

def extract_phone(text):
    """Извлекаем телефон из текста"""
    import re
    phones = re.findall(r'[\+]?[0-9\s\-\(\)]{10,20}', text)
    if phones:
        return phones[0].strip()
    return ''

def parse_category(text):
    """Определяем категорию по ключевым словам"""
    text_lower = text.lower()
    
    categories = {
        'ремонт': ['ремонт', 'отделка', 'плитка', 'поклейка', 'покраска'],
        'сантехника': ['сантехник', 'вода', 'канализация', 'трубы', 'унитаз'],
        'электрика': ['электрик', 'проводка', 'розетка', 'свет', 'электр'],
        'строительство': ['строитель', 'кладка', 'бетон', 'фундамент'],
        'грузчики': ['грузчик', 'вывоз', 'переезд', 'разгрузка'],
        'уборка': ['уборка', 'клининг', 'мойка'],
    }
    
    for category, keywords in categories.items():
        if any(kw in text_lower for kw in keywords):
            return category
    
    return 'другое'

def parse_city(text):
    """Определяем город"""
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
    
    # Тестируем подключение
    if not test_connection():
        exit(1)
    
    # Запускаем парсер
    get_channel_updates()