import os
import requests
from supabase import create_client
from datetime import datetime

# Telegram Bot
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL = '@dnrsabbath'

# Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

print(f" Подключение к Supabase...")
print(f"URL: {SUPABASE_URL}")
print(f"Key starts with: {SUPABASE_KEY[:20] if SUPABASE_KEY else 'None'}...")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Успешно подключились к Supabase!")
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
    exit(1)

def get_channel_updates():
    """Получаем новые сообщения из канала"""
    
    print("📥 Получаем последнее состояние парсера...")
    
    # Получаем последний ID из базы
    try:
        state = supabase.table('parser_state').select('*').eq('id', 1).execute()
        last_id = state.data[0]['last_message_id'] if state.data else 0
        print(f"Последний message_id: {last_id}")
    except Exception as e:
        print(f"❌ Ошибка чтения parser_state: {e}")
        # Создаем таблицу если нет
        print("📝 Создаем таблицу parser_state...")
        supabase.table('parser_state').insert({'id': 1, 'last_message_id': 0}).execute()
        last_id = 0
    
    # Запрашиваем обновления через Bot API
    print(f" Запрашиваем обновления из канала...")
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates'
    params = {
        'offset': last_id + 1,
        'limit': 100,
        'timeout': 30
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if not data.get('ok'):
            print(f"❌ Telegram API error: {data}")
            return
        
        results = data.get('result', [])
        print(f"📬 Получено {len(results)} обновлений")
        
        new_ads = []
        max_id = last_id
        
        for update in results:
            # Проверяем, что это сообщение из канала
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
            try:
                supabase.table('ads').insert(new_ads).execute()
                print("✅ Объявления сохранены!")
            except Exception as e:
                print(f"❌ Ошибка сохранения ads: {e}")
            
            # Обновляем состояние
            print("🔄 Обновляем состояние парсера...")
            supabase.table('parser_state').update({
                'last_message_id': max_id,
                'updated_at': datetime.now().isoformat()
            }).eq('id', 1).execute()
            
            print(f"\n🎉 Готово! Добавлено {len(new_ads)} объявлений")
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
    get_channel_updates()