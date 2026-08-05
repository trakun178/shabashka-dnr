# 🕸️ Шабашка DNR — Сайт объявлений

Веб-сайт-витрина объявлений из Telegram-каналов «Шабашка DNR» (Донецк, Макеевка и область). Автоматически парсит посты из Telegram, публикует их в VK и отображает на своём сайте с фильтрацией по категориям и городам.

## ✨ Возможности

- 🏠 **Статический фронтенд** на Next.js — быстрая загрузка, SEO-оптимизация
- 📋 **Карточки объявлений** с фото, описанием, ценой и контактами
- 🔍 **Фильтрация** по категориям (ремонт, строительство, электрика, сантехника) и городам (Донецк, Макеевка, Горловка, Енакиево)
- 🔎 **Поиск** по тексту объявлений на лету
- 📱 **PWA-поддержка** — можно установить как приложение на телефон
- 🤖 **GitHub Actions парсер** — каждые 15 минут собирает новые объявления из Telegram
- 📢 **Автопостинг в VK** — дублирует объявления в группу ВКонтакте
- 🗺️ **SEO**: robots.txt, sitemap.xml, OpenGraph, Twitter Cards, canonical URL

## 🏗 Архитектура

```
shabashka-dnr/
├── index.html           # PWA entry point + fallback
├── manifest.json        # PWA-манифест
├── robots.txt           # Правила индексации
├── sitemap.xml          # Карта сайта
├── vercel.json          # Конфигурация Vercel
├── frontend/
│   ├── app/
│   │   ├── page.tsx              # Главная страница (лента объявлений)
│   │   ├── ad/[id]/page.tsx      # Детальная страница объявления
│   │   ├── category/[category]/  # Фильтр по категории
│   │   ├── robots.ts             # Динамический robots.txt
│   │   └── sitemap.ts            # Динамический sitemap.xml
│   ├── lib/api.ts                # API-клиент к Supabase
│   ├── public/                   # Статика (манифест, иконки)
│   └── wrangler.toml             # Конфиг Cloudflare Pages (опционально)
├── parser/
│   ├── main.py           # Парсер Telegram → Supabase
│   ├── vk_uploader.py    # Публикация в VK (wall.post + фото)
│   └── requirements.txt  # Зависимости парсера
├── images/               # Иконки и фавиконы всех размеров
└── .github/workflows/
    ├── parser.yml        # Cron-парсер (каждые 15 мин, 03:00–22:00 МСК)
    └── test-secrets.yml  # Проверка секретов
```

### 🔄 Поток данных

```
Telegram-канал → Парсер (GitHub Actions) → Supabase → Фронтенд (Next.js/Vercel)
                                          ↘ VK-группа (vk_uploader)
```

### 📡 Парсер (`parser/main.py`)

- Подключается к Telegram через Bot API
- Читает последние сообщения из канала-источника
- Извлекает: текст, фото, телефон, ссылки, дату
- Сохраняет в Supabase (таблица `ads`)
- Обновляет `parser_state.last_message_id` для инкрементальной загрузки
- Вызывает `vk_uploader.py` для дублирования поста в VK

## 📦 Технологический стек

| Компонент   | Технология                          |
| ----------- | ----------------------------------- |
| Фронтенд    | Next.js (App Router), TypeScript    |
| Хостинг     | Vercel                              |
| База данных | Supabase (REST API)                 |
| Парсер      | Python 3.11 + `python-telegram-bot` |
| VK API      | `vk-api` (wall.post, photos)        |
| Cron        | GitHub Actions                      |
| PWA         | Web App Manifest + Service Worker   |

## 🔑 Переменные окружения

### Фронтенд (`frontend/.env.local`)

| Переменная                 | Назначение              |
| -------------------------- | ----------------------- |
| `NEXT_PUBLIC_SUPABASE_URL` | URL Supabase            |
| `NEXT_PUBLIC_SUPABASE_KEY` | Публичный ключ Supabase |

### Парсер (`parser/.env` и GitHub Secrets)

| Переменная     | Назначение                   |
| -------------- | ---------------------------- |
| `BOT_TOKEN`    | Токен Telegram-бота парсера  |
| `SUPABASE_URL` | URL Supabase                 |
| `SUPABASE_KEY` | Ключ Supabase (service_role) |
| `VK_TOKEN`     | Токен VK API                 |
| `VK_GROUP_ID`  | ID группы VK (отрицательный) |

## 🚀 Деплой

### Сайт (Vercel)

1. Подключите репозиторий к Vercel
2. Укажите Framework Preset: Next.js
3. Добавьте переменные окружения из `frontend/.env.local`

### Парсер (GitHub Actions)

1. Добавьте секреты в Settings → Secrets and variables → Actions
2. Парсер запускается автоматически по cron: `*/15 3-22 * * *` (каждые 15 минут с 03:00 до 22:00 МСК)
3. Ручной запуск: Actions → Parser → Run workflow

## 🌐 Продакшен-URL

https://shabashka.sofoniya.ru

## 📄 Лицензия

Проприетарный код. Использование только в рамках проекта «Шабашка DNR».
