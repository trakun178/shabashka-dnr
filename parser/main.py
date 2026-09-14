import os
import re
import json
import time
from datetime import datetime, timezone, timedelta

import requests
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    print("📁 Загружаем переменные из .env файла...")
    load_dotenv(env_path)
    print(f"   Путь: {env_path}")
else:
    print("ℹ️ .env файл не найден, используем GitHub Secrets...")

print("\n🔍 Проверка переменных окружения:")
print("=" * 50)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '').strip()
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').strip()
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '').strip()
VK_TOKEN = os.environ.get('VK_TOKEN', '').strip()
VK_GROUP_ID = os.environ.get('VK_GROUP_ID', '').strip()

print(f"  BOT_TOKEN: {'✅' if BOT_TOKEN else '❌'}")
print(f"  SUPABASE_URL: {'✅' if SUPABASE_URL else '❌'}")
print(f"  SUPABASE_KEY: {'✅' if SUPABASE_KEY else '❌'}")
print(f"  SUPABASE_KEY формат: {'JWT ✅' if SUPABASE_KEY.startswith('eyJ') and SUPABASE_KEY.count('.') == 2 else 'НЕ JWT ❌'}")
print(f"  VK_TOKEN: {'✅' if VK_TOKEN else '❌'}")
print(f"  VK_GROUP_ID: {'✅' if VK_GROUP_ID else '❌'}")
print("=" * 50)

# ✅ Лимит VK на размер одного фото
VK_MAX_PHOTO_BYTES = 5 * 1024 * 1024

vk_uploader = None
normalize_image = None
if VK_TOKEN and VK_GROUP_ID:
    try:
        from vk_uploader import VKUploader, normalize_image
        vk_uploader = VKUploader(VK_TOKEN, VK_GROUP_ID)
    except Exception as e:
        print(f"❌ Ошибка инициализации VK: {e}")
        vk_uploader = None
        normalize_image = None

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL или SUPABASE_KEY не установлены!")
    exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}


def mask_secret(text):
    """✅ Прячем токен бота из логов."""
    if text and BOT_TOKEN:
        return str(text).replace(BOT_TOKEN, '***')
    return text


def get_file_url(file_id):
    """Временная ссылка Telegram (~1 час жизни). Используется ТОЛЬКО для
    скачивания фото и НИКОГДА не сохраняется в БД."""
    try:
        file_url = f'https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}'
        file_response = requests.get(file_url, timeout=30)
        file_data = file_response.json()
        if file_data.get('ok'):
            return f'https://api.telegram.org/file/bot{BOT_TOKEN}/{file_data["result"]["file_path"]}'
    except Exception as e:
        print(f"  ⚠️ Ошибка получения файла: {mask_secret(e)}")
    return None


def upload_photo_to_storage(content: bytes, message_id: int):
    """✅ Кладёт фото в Supabase Storage (бакет ads), возвращает постоянную
    публичную ссылку без токена бота."""
    name = f"{message_id}.jpg"
    try:
        r = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/ads/{name}",
            headers={
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "image/jpeg",
                "x-upsert": "true",
            },
            data=content,
            timeout=60,
        )
        if r.ok:
            print(f"   ☁️ Фото в хранилище: {name}")
            return f"{SUPABASE_URL}/storage/v1/object/public/ads/{name}"
        print(f"   ❌ Supabase Storage: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"   ❌ Ошибка загрузки в хранилище: {e}")
    return None


def download_and_store(file_id, message_id):
    """✅ Скачивает фото из Telegram, нормализует и сохраняет в Storage.
    Возвращает постоянную ссылку (её можно отдавать и сайту, и VK)."""
    tg_url = get_file_url(file_id)
    if not tg_url:
        return None
    try:
        r = requests.get(tg_url, timeout=30)
        if r.status_code != 200 or not r.content:
            print(f"   ❌ Не удалось скачать фото из Telegram (код {r.status_code})")
            return None
        content = normalize_image(r.content) if normalize_image else r.content
        return upload_photo_to_storage(content, message_id)
    except Exception as e:
        print(f"   ⚠️ Ошибка скачивания/обработки фото: {e}")
        return None


def pick_photo_size(sizes):
    """✅ Выбирает НАИБОЛЬШИЙ размер фото, проходящий под лимит VK (≤ 5 МБ)."""
    if not sizes:
        return None
    with_size = [s for s in sizes if (s.get('file_size') or 0) > 0]
    fit = [s for s in with_size if s['file_size'] <= VK_MAX_PHOTO_BYTES]
    if fit:
        return max(fit, key=lambda s: s.get('width', 0))
    without_size = [s for s in sizes if (s.get('file_size') or 0) == 0]
    if without_size:
        return min(without_size, key=lambda s: s.get('width', 0))
    return None


def extract_media(post):
    """✅ Возвращает (photo_urls, has_media).
    photo_urls — ПОСТОЯННЫЕ ссылки из Supabase Storage (не временные Telegram):
    их безопасно хранить в БД и отдавать сайту, даже когда VK на паузе.
    Видео и не-изображения как фото больше НЕ отправляются."""
    photo_urls = []
    has_media = False

    if post.get('photo'):
        has_media = True
        size = pick_photo_size(post['photo'])
        if size:
            url = download_and_store(size['file_id'], post['message_id'])
            if url:
                photo_urls.append(url)
        else:
            print("   ⚠️ Все размеры фото тяжелее 5 МБ — фото пропускается")
    elif post.get('document'):
        has_media = True
        doc = post['document']
        mime = (doc.get('mime_type') or '').lower()
        fsize = doc.get('file_size') or 0
        if mime.startswith('image/') and fsize <= VK_MAX_PHOTO_BYTES:
            url = download_and_store(doc['file_id'], post['message_id'])
            if url:
                photo_urls.append(url)
        else:
            print(f"   ⚠️ Документ не подходит как фото (mime={mime}, size={fsize}) — пост уйдёт текстом")
    elif post.get('video') or post.get('animation') or post.get('video_note'):
        has_media = True
        print("   ⚠️ Видео/анимация в фото не конвертируются — пост уйдёт текстом со ссылкой")

    return photo_urls, has_media


def extract_phone(text):
    if not text:
        return ''
    phones = re.findall(r'\+?\d{10,15}', text)
    return phones[0] if phones else ''


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
    if 'макеевка' in text_lower:
        return 'Макеевка'
    if 'горловка' in text_lower:
        return 'Горловка'
    return 'Донецк'


def smart_title(text, max_length=70):
    if not text or len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
    stop_words = ['а', 'и', 'в', 'на', 'не', 'при', 'но', 'или', 'если', 'бы', 'ли', 'же', 'то',
                  'как', 'так', 'для', 'без', 'под', 'над', 'из', 'с', 'к', 'по', 'до', 'от', 'за', 'о', 'об']
    words = truncated.split()
    while words and words[-1].lower().strip('.,!?;:') in stop_words:
        words.pop()
    return ' '.join(words) if words else text[:max_length]


def pause_vk(hours=48):
    """⛔ Полная тишина в VK на N часов: пишем метку в parser_state,
    следующие прогоны до этого момента не делают к VK ни одного запроса."""
    until = (datetime.now(timezone(timedelta(hours=3))) + timedelta(hours=hours)).isoformat()
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/parser_state?id=eq.1",
        headers=HEADERS,
        json={'vk_blocked_until': until}
    )
    print(f"⛔ Error 9: полная пауза VK на {hours} ч (до {until}), статус записи: {r.status_code}")
    return None


def get_channel_updates():
    global vk_uploader

    print("\n" + "=" * 50)
    print("🚀 Запуск парсера Telegram канала")
    print("=" * 50)

    url = f"{SUPABASE_URL}/rest/v1/parser_state?id=eq.1"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"❌ Ошибка чтения parser_state: {response.status_code}")
        return

    data = response.json()
    last_id = data[0]['last_message_id'] if data else 0

    # ⛔ Проверка паузы VK (Error 9): пока метка активна — ноль запросов к VK
    vk_blocked_until = None
    if data:
        raw = data[0].get('vk_blocked_until')
        if raw:
            try:
                vk_blocked_until = datetime.fromisoformat(raw)
            except ValueError:
                vk_blocked_until = None
    if vk_blocked_until and vk_blocked_until > datetime.now(timezone(timedelta(hours=3))):
        print(f"⛔ VK на паузе до {vk_blocked_until.isoformat()} — работаем только с сайтом, ноль запросов к VK")
        vk_uploader = None

    ads_url = f"{SUPABASE_URL}/rest/v1/ads?order=tg_message_id.desc&limit=1"
    ads_response = requests.get(ads_url, headers=HEADERS)
    real_last_id = 0
    if ads_response.status_code == 200:
        ads_data = ads_response.json()
        if ads_data and len(ads_data) > 0:
            real_last_id = ads_data[0]['tg_message_id']

    if real_last_id > last_id:
        last_id = real_last_id

    print(f"✅ Будем искать сообщения > {last_id}")

    telegram_url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates'
    params = {'limit': 100, 'timeout': 30, 'offset': last_id + 1}

    data = None
    for attempt in range(3):
        try:
            response = requests.get(telegram_url, params=params, timeout=60,
                                    headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    break
        except Exception:
            time.sleep(10)
            continue

    if not data or not data.get('ok'):
        print("❌ Не удалось подключиться к Telegram")
        return

    all_updates = data.get('result', [])
    results = [u for u in all_updates if 'channel_post' in u and u['channel_post']['message_id'] > last_id]

    if not results:
        print("ℹ️ Новых сообщений нет.")
        return

    groups = {}
    single_messages = []
    for update in results:
        post = update['channel_post']
        media_group_id = post.get('media_group_id')
        if media_group_id:
            groups.setdefault(media_group_id, []).append(post)
        else:
            single_messages.append(post)

    new_ads = []
    max_id = last_id
    saved_count = 0
    vk_posts_count = 0

    # 7. Обрабатываем альбомы
    group_keys = list(groups.keys())
    for idx, media_group_id in enumerate(group_keys):
        posts = groups[media_group_id]
        main_post = posts[0]
        message_id = main_post['message_id']
        tg_date = datetime.fromtimestamp(main_post['date'], tz=timezone.utc)
        created_at_msk = tg_date.astimezone(timezone(timedelta(hours=3)))

        combined_text = '\n'.join(
            post.get('text') or post.get('caption', '')
            for post in posts if post.get('text') or post.get('caption')
        ).strip()

        # ✅ Сброс для каждого альбома. В photo_urls — постоянные ссылки Storage
        photo_urls = []
        has_media = False
        for post in posts:
            urls, media = extract_media(post)
            photo_urls.extend(urls)
            has_media = has_media or media

        print(f"  📸 Фото для VK: {len(photo_urls)}")
        if photo_urls:
            print(f"  🔍 Пример URL: {mask_secret(photo_urls[0])[:100]}...")

        post_link = f"https://t.me/{main_post.get('chat', {}).get('username', 'dnrsabbath')}/{message_id}"
        forwarded_from = main_post.get('forward_sender_name') or (
            main_post.get('forward_from_chat', {}).get('title')
            if 'forward_from_chat' in main_post else None
        )

        vk_result = None
        if vk_uploader and (combined_text or has_media):
            print("  📤 Публикуем пост в VK...")
            print(f"     Текст: {len(combined_text)} символов")
            print(f"     Фото: {len(photo_urls)} шт.")
            print(f"  📦 Отправляем в VK:")
            print(f"     Сообщение: {(combined_text or '')[:100]}...")
            if photo_urls:
                print(f"     Фото URL: {mask_secret(photo_urls[0])[:80]}...")

            vk_result = vk_uploader.post_with_photos(
                message=combined_text[:4096],
                photo_urls=photo_urls if photo_urls else None,
                forwarded_from=forwarded_from,
                post_link=post_link
            )
            if vk_result is None and vk_uploader and getattr(vk_uploader, 'flood_blocked', False):
                vk_uploader = pause_vk(48)
            if vk_result:
                vk_posts_count += 1
                print(f"  ✅ Пост в VK: {vk_result['post_url']}")

                # ✅ УМНАЯ ЗАДЕРЖКА: только если это не последний пост
                is_last_album = (idx == len(group_keys) - 1) and (len(single_messages) == 0)
                if not is_last_album:
                    print("  ⏱️ Ожидание 180 секунд перед следующим постом...")
                    time.sleep(180)

        if combined_text or has_media:
            vk_post_url = vk_result['post_url'] if vk_result else None

            # ✅ Приоритет — CDN VK (быстро из РФ). Если VK на паузе или не принял
            #    фото — сохраняем постоянные ссылки из Supabase Storage:
            #    сайт остаётся С ФОТО при любом состоянии VK.
            final_photo_urls = (vk_result.get('photo_urls') or []) if vk_result else []
            if not final_photo_urls:
                final_photo_urls = photo_urls if photo_urls else []
            final_photo_url = final_photo_urls[0] if final_photo_urls else None

            new_ads.append({
                'tg_message_id': message_id,
                'title': smart_title(combined_text) if combined_text else f"Объявление #{message_id}",
                'description': combined_text or "Объявление с медиа файлом",
                'category': parse_category(combined_text),
                'city': parse_city(combined_text),
                'phone': extract_phone(combined_text),
                'photo_url': final_photo_url,
                'photo_urls': json.dumps(final_photo_urls),
                'vk_post_url': vk_post_url,
                'post_link': post_link,
                'forwarded_from': forwarded_from,
                'created_at': created_at_msk.isoformat()
            })
            # ✅ Учитываем ID всех сообщений альбома
            max_id = max(max_id, *[p['message_id'] for p in posts])
            saved_count += 1

    # 8. Обрабатываем одиночные сообщения
    for idx, post in enumerate(single_messages):
        message_id = post['message_id']
        tg_date = datetime.fromtimestamp(post['date'], tz=timezone.utc)
        created_at_msk = tg_date.astimezone(timezone(timedelta(hours=3)))

        text = post.get('text') or post.get('caption', '')
        channel_username = post.get('chat', {}).get('username', 'dnrsabbath')
        post_link = f"https://t.me/{channel_username}/{message_id}"

        forwarded_from = None
        if 'forward_from' in post:
            sender = post['forward_from']
            forwarded_from = f"{sender.get('first_name', '')} {sender.get('last_name', '')}".strip()
            if sender.get('username'):
                forwarded_from += f" (@{sender['username']})"
        elif 'forward_from_chat' in post:
            chat = post['forward_from_chat']
            forwarded_from = chat.get('title', 'Unknown')
            if chat.get('username'):
                forwarded_from += f" (@{chat['username']})"
        elif 'forward_sender_name' in post:
            forwarded_from = post['forward_sender_name'] or "Скрытый профиль"

        # ✅ Сброс для каждого сообщения
        photo_urls, has_media = extract_media(post)

        print(f"   📸 Фото для VK: {len(photo_urls)}")
        if photo_urls:
            print(f"   🔍 Пример URL: {mask_secret(photo_urls[0])[:100]}...")

        vk_result = None
        if vk_uploader and (text or has_media):
            print("   📤 Публикуем пост в VK...")
            print(f"      Текст: {len(text)} символов")
            print(f"      Фото: {len(photo_urls)} шт.")
            print("   📦 Отправляем в VK:")
            print(f"      Сообщение: {(text or '')[:100]}...")
            if photo_urls:
                print(f"      Фото URL: {mask_secret(photo_urls[0])[:80]}...")

            vk_result = vk_uploader.post_with_photos(
                message=text[:4096],
                photo_urls=photo_urls if photo_urls else None,
                forwarded_from=forwarded_from,
                post_link=post_link
            )
            if vk_result is None and vk_uploader and getattr(vk_uploader, 'flood_blocked', False):
                vk_uploader = pause_vk(48)
            if vk_result:
                vk_posts_count += 1
                print(f"  ✅ Пост в VK: {vk_result['post_url']}")

                # ✅ УМНАЯ ЗАДЕРЖКА: только если это не последний пост
                if idx < len(single_messages) - 1:
                    print("  ⏱️ Ожидание 180 секунд перед следующим постом...")
                    time.sleep(180)

        if text or has_media:
            vk_post_url = vk_result['post_url'] if vk_result else None

            # ✅ Приоритет — CDN VK, фолбэк — Supabase Storage
            final_photo_urls = (vk_result.get('photo_urls') or []) if vk_result else []
            if not final_photo_urls:
                final_photo_urls = photo_urls if photo_urls else []
            final_photo_url = final_photo_urls[0] if final_photo_urls else None

            new_ads.append({
                'tg_message_id': message_id,
                'title': smart_title(text) if text else f"Объявление #{message_id}",
                'description': text or "Объявление с медиа файлом",
                'category': parse_category(text),
                'city': parse_city(text),
                'phone': extract_phone(text),
                'photo_url': final_photo_url,
                'photo_urls': json.dumps(final_photo_urls),
                'vk_post_url': vk_post_url,
                'post_link': post_link,
                'forwarded_from': forwarded_from,
                'created_at': created_at_msk.isoformat()
            })
            max_id = max(max_id, message_id)
            saved_count += 1

    print(f"\n📊 Итог: {saved_count} объявлений, {vk_posts_count} постов в VK")

    # 9. Сохраняем в Supabase
    if new_ads:
        print(f"\n💾 Сохраняем {len(new_ads)} объявлений...")
        url = f"{SUPABASE_URL}/rest/v1/ads"
        headers_upsert = HEADERS.copy()
        headers_upsert["Prefer"] = "resolution=ignore-duplicates,return=representation"
        response = requests.post(url, headers=headers_upsert, json=new_ads)

        # ✅ 10. Обновляем last_message_id ТОЛЬКО ПРИ УСПЕШНОМ СОХРАНЕНИИ
        if response.status_code in [200, 201]:
            print("✅ Объявления успешно сохранены в базу!")

            url_state = f"{SUPABASE_URL}/rest/v1/parser_state?id=eq.1"
            state_response = requests.patch(url_state, headers=HEADERS, json={
                'last_message_id': max_id,
                'updated_at': datetime.now(timezone(timedelta(hours=3))).isoformat()
            })

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