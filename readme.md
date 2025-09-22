# GoodRobot — Telegram Bot для поиска мастеров

Новый Telegram-бот, который помогает клиентам быстро находить мастеров по категориям и районам. Построен на современном стеке: aiogram 3.x, SQLAlchemy 2.x (async), Alembic, Pydantic v2.

## Возможности
- Выбор роли: клиент, мастер, партнёр (WIP)
- Клиент: создание заявки (категория → район → адрес → описание)
- Мастер: настройка районов (мультивыбор с кнопками Готово/Сброс)
- Уведомления мастерам по выбранному району + кнопка «Откликнуться»
- Создание ставок (Bid) мастерами
- БД-модели: User, Order, Bid, Rating, Partner, Payout
- Индексы для ускорения выборок: Order(category, zone, status), Bid(order_id, created_at)

## Скриншоты

<p>
  <img src="docs/images/role_selection.svg" alt="Выбор роли" width="720" />
</p>
<p>
  <img src="docs/images/master_zones.svg" alt="Настройка зон мастера" width="720" />
</p>

## Технологии
- Python 3.11
- aiogram==3.x
- SQLAlchemy==2.x (async) + asyncpg, greenlet
- Alembic (миграции)
- Pydantic v2 + pydantic-settings

## Быстрый старт (локально)
1) Установите зависимости
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2) Настройте переменные окружения (`.env`)
```ini
BOT_TOKEN=123456:ABC...
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=masterbot
POSTGRES_USER=masterbot
POSTGRES_PASSWORD=masterbot
# Либо альтернативно единым DSN:
# POSTGRES_DSN=postgresql+asyncpg://user:pass@host:5432/dbname
```

3) Примените миграции
```bash
alembic upgrade head
```

4) Запустите бота
```bash
source venv/bin/activate
python -m app.bot.main
```

Примечание: если получаете TelegramConflictError — убедитесь, что запущен только один экземпляр бота и вебхук удалён:
```bash
curl "https://api.telegram.org/bot$BOT_TOKEN/deleteWebhook"
```

## AI: Gemini 2.0 (короткие ответы) + локальный фоллбек

Бот использует облачную модель Gemini 2.0 (по умолчанию `gemini-2.0-flash`) и автоматически переключается на локальную HF-модель (CPU), если ключ не задан или сервис недоступен.

Переменные окружения (см. `.env.example`):

```ini
# Ключ Gemini (канонично)
API_GEMINI_FREE=your_gemini_api_key_here

# Модель Gemini по умолчанию
GEMINI_MODEL_NAME=gemini-2.0-flash

# Локальная модель-фоллбек
AI_MODEL_NAME=cointegrated/rut5-base-multitask

# Короткие ответы (по умолчанию 60 токенов)
AI_MAX_NEW_TOKENS=60
```

Важно:
- Никогда не коммитьте `.env` c реальными секретами. Используйте `.env.example` как шаблон.
- Если `.env` попал в git-историю, выполните `git rm --cached .env` и смените ключи (ротация токенов).
- Ответы намеренно краткие (1–2 предложения) для удобства в Telegram.

## Запуск админки (Streamlit)

Для запуска админ-панели на базе Streamlit выполните следующие команды:

```bash
# Активация виртуального окружения
source venv/bin/activate

# Установка зависимостей (если ещё не установлены)
pip install streamlit pandas plotly

# Запуск админки
streamlit run admin_streamlit/app.py
```

После запуска админ-панель будет доступна по адресу http://localhost:8501

## Структура проекта
```
app/
  bot/
    handlers/ (client.py, master.py, partner.py)
    keyboards.py
    states.py
    main.py
  models/
    __init__.py, user.py, order.py, bid.py, rating.py, partner.py, payout.py
admin_streamlit/  # Новая админка на Streamlit
  app.py          # Основной файл приложения
  pages/          # Страницы админки
  utils/          # Утилиты для админки
core/
  config.py
  db.py
alembic/
  env.py, versions/
README.md
requirements.txt
.env.example
.gitignore
```

## Модели и бизнес-логика (кратко)
- `User`: роли, `zones: ARRAY(TEXT)` для мастеров
- `Order`: связь с клиентом, категория, зона, адрес, описание, индекс `(category, zone, status)`
- `Bid`: ставка мастера для заказа, индекс `(order_id, created_at)`
- `Payout`: комиссия/выплата при завершении заказа (WIP: расчёт и фиксация на событии завершения)

## Дорожная карта
- [x] Роли, заявки, зоны мастеров, ставки
- [x] Админ-панель (Streamlit)
- [ ] Окно ставок (2 минуты) и выбор мастера клиентом
- [ ] Завершение заказа и расчёт `Payout` (85/10/5)
- [ ] Рейтинг и отзывы
- [ ] Вебхуки

## Ветки и процесс разработки
- `main` — стабильные релизы
- `dev` — активная разработка

Процесс:
1) Коммитим в `dev` → создаём PR → проверка → мердж в `main`.
2) Теги/релизы по необходимости.

## Лицензия
TBD
