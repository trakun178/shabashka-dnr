# ═══════════════════════════════════════════════════════════════
#  ПАТЧ ДЛЯ main.py — против повторного Error 9
#  Заменить указанные куски, остальное не трогать.
# ═══════════════════════════════════════════════════════════════

# ── 0. Сначала в Supabase, иначе пауза не сохранится вовсе ──
#
#   alter table parser_state add column if not exists vk_blocked_until timestamptz;
#   alter table parser_state add column if not exists vk_album_id      bigint;
#   alter table parser_state add column if not exists vk_posts_today   int default 0;
#   alter table parser_state add column if not exists vk_posts_date    date;


# ── 1. Инициализация аплоадера (строки 38-47) ──────────────────
# Альбом запоминается в БД, иначе photos.createAlbum может вызваться повторно.

VK_ALBUM_ID = None          # заполняется ниже, после чтения parser_state


def save_album_id(album_id):
    """Колбэк аплоадера: запоминаем служебный альбом навсегда."""
    try:
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/parser_state?id=eq.1",
            headers=HEADERS,
            json={"vk_album_id": album_id},
            timeout=30,
        )
        print(f"   💾 album_id сохранён: {album_id}")
    except Exception as e:
        print(f"   ⚠️ album_id не сохранён: {e}")


# В get_channel_updates(), сразу после чтения parser_state:
#
#     VK_ALBUM_ID = data[0].get('vk_album_id') if data else None
#     if VK_TOKEN and VK_GROUP_ID and vk_uploader is None:
#         from vk_uploader import VKUploader, normalize_image
#         vk_uploader = VKUploader(VK_TOKEN, VK_GROUP_ID,
#                                  album_id=VK_ALBUM_ID,
#                                  on_album_created=save_album_id)


# ── 2. Разбор vk_blocked_until (строки 256-267) ────────────────
# datetime.fromisoformat падает на суффиксе "Z" в Python < 3.11,
# и тогда пауза молча игнорируется — парсер снова идёт в VK.

def parse_ts(raw):
    """Терпимый разбор времени из Supabase. None — если разобрать нельзя."""
    if not raw:
        return None
    s = str(raw).strip().replace("Z", "+00:00")
    # микросекунды иногда приходят длиннее шести знаков
    import re as _re
    s = _re.sub(r"\.(\d{6})\d+", r".\1", s)
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        print(f"   ⚠️ Не разобрано время: {raw!r} — считаем, что паузы нет")
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=3)))
    return dt


# Заменить блок чтения паузы на:
#
#     vk_blocked_until = parse_ts(data[0].get('vk_blocked_until')) if data else None
#     if vk_blocked_until and vk_blocked_until > datetime.now(timezone(timedelta(hours=3))):
#         print(f"⛔ VK на паузе до {vk_blocked_until.isoformat()}")
#         vk_uploader = None


# ── 3. pause_vk: проверять, что пауза РЕАЛЬНО записалась ───────
# Прежняя версия печатала код ответа и шла дальше. Если колонки нет,
# Supabase отвечает 400, пауза теряется, следующий запуск снова ловит Error 9.

def pause_vk(hours=6):
    """Пауза VK на N часов. Возвращает None (чтобы обнулить vk_uploader)."""
    until = (datetime.now(timezone(timedelta(hours=3))) + timedelta(hours=hours)).isoformat()
    try:
        r = requests.patch(
            f"{SUPABASE_URL}/rest/v1/parser_state?id=eq.1",
            headers=HEADERS,
            json={'vk_blocked_until': until},
            timeout=30,
        )
        if r.status_code not in (200, 204):
            print("🚨 ПАУЗА НЕ СОХРАНЕНА! "
                  f"Supabase: {r.status_code} {r.text[:200]}")
            print("🚨 Добавьте колонку: "
                  "alter table parser_state add column if not exists vk_blocked_until timestamptz;")
        else:
            print(f"⛔ Error 9: пауза VK на {hours} ч, до {until}")
    except Exception as e:
        print(f"🚨 Пауза не сохранена (сеть): {e}")
    return None


# ── 4. Пауза должна расти, а не быть всегда 48 ч ───────────────
# Первая девятка часто разжимается за час. Сразу ставить двое суток —
# терять посты на ровном месте. Считаем подряд идущие срабатывания.

def pause_vk_progressive(state_row):
    """1-я девятка — 1 ч, 2-я подряд — 6 ч, 3-я и дальше — 24 ч."""
    streak = int((state_row or {}).get('vk_flood_streak') or 0) + 1
    hours = {1: 1, 2: 6}.get(streak, 24)
    try:
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/parser_state?id=eq.1",
            headers=HEADERS,
            json={'vk_flood_streak': streak},
            timeout=30,
        )
    except Exception:
        pass
    return pause_vk(hours)
# Колонка: alter table parser_state add column if not exists vk_flood_streak int default 0;
# Сбрасывать в 0 после успешного поста:
#     requests.patch(..., json={'vk_flood_streak': 0})


# ── 5. Дневной лимит постов ────────────────────────────────────
# Стена сообщества не рассчитана на поток из парсера. Даже без ошибок
# VK начинает резать при десятках постов в сутки. Держим потолок сами.

VK_DAILY_POST_LIMIT = 20


def vk_quota_left(state_row):
    """Сколько постов ещё можно опубликовать сегодня."""
    today = datetime.now(timezone(timedelta(hours=3))).date().isoformat()
    if (state_row or {}).get('vk_posts_date') != today:
        return VK_DAILY_POST_LIMIT
    return max(0, VK_DAILY_POST_LIMIT - int(state_row.get('vk_posts_today') or 0))


def vk_quota_bump(used):
    today = datetime.now(timezone(timedelta(hours=3))).date().isoformat()
    try:
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/parser_state?id=eq.1",
            headers=HEADERS,
            json={'vk_posts_today': used, 'vk_posts_date': today},
            timeout=30,
        )
    except Exception:
        pass


# Перед публикацией:
#     if vk_quota_left(state_row) <= 0:
#         print("⏸ Дневной лимит постов в VK исчерпан — только сайт")
#         vk_uploader = None


# ── 6. time.sleep(180) внутри GitHub Actions ───────────────────
# Пять постов = 12 минут простоя оплаченного раннера, и при этом всё равно
# упираемся в суточный лимит VK. Лучше публиковать по одному посту за запуск,
# а частоту задавать расписанием workflow:
#
#     on:
#       schedule:
#         - cron: '*/20 * * * *'
#
# и в коде обрывать цикл после первого успешного вк-поста:
#
#     if vk_result:
#         vk_posts_count += 1
#         vk_uploader = None       # остальные посты этого запуска — только на сайт
#
# Сайт при этом наполняется всеми объявлениями сразу: фото уже лежат
# в Supabase Storage и от VK не зависят.
