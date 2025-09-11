# 📚 API Документация GoodRobot

## 🚀 Обзор
API админ-панели GoodRobot предоставляет RESTful интерфейс для управления мастерами, категориями и администраторами.

## 🔐 Аутентификация
Все API запросы требуют JWT токена в заголовке `Authorization: Bearer <token>`

```bash
# Получение токена
POST /token
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin123&grant_type=password

# Использование токена
GET /masters/1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

## 👥 Управление мастерами

### Получение списка мастеров
```http
GET /masters/api?skip=0&limit=10
Authorization: Bearer <token>
```

**Параметры:**
- `skip` (int): Количество пропускаемых записей (по умолчанию: 0)
- `limit` (int): Максимальное количество записей (по умолчанию: 10)
- `is_active` (bool, опционально): Фильтр по статусу активности
- `search` (str, опционально): Поиск по имени или username

**Ответ:**
```json
[
  {
    "id": 1,
    "username": "master1",
    "full_name": "Иван Иванов",
    "telegram_id": 123456789,
    "is_active": true,
    "specialties": ["Электрика", "Сантехника"],
    "created_at": "2025-01-01T10:00:00"
  }
]
```

### Получение деталей мастера
```http
GET /masters/{master_id}
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "master": {
    "id": 1,
    "name": "Иван Иванов",
    "username": "master1",
    "email": "master1@example.com",
    "phone": "+7(999)123-45-67",
    "is_active": true,
    "categories": ["Электрика", "Сантехника"],
    "specialties": ["Электрик", "Сантехник"]
  },
  "all_categories": ["Электрика", "Сантехника", "Бытовая техника", "Клининг"],
  "all_specialties": ["Электрик", "Сантехник", "Плотник", "Маляр"],
  "master_stats": {
    "completed_orders": 15,
    "active_orders": 2
  }
}
```

### Обновление категорий мастера
```http
POST /api/masters/{master_id}/categories
Authorization: Bearer <token>
Content-Type: application/json
```

**Тело запроса:**
```json
{
  "categories": ["Электрика", "Сантехника"]
}
```

**Валидация:**
- Минимум 1 категория, максимум 10
- Категории должны быть из допустимого списка
- Дубликаты автоматически удаляются
- Пустые строки игнорируются

**Ответ:**
```json
{
  "categories": ["Электрика", "Сантехника"],
  "master_id": 1,
  "updated_at": "2025-01-01T12:00:00"
}
```

### Блокировка/разблокировка мастера
```http
POST /api/masters/{master_id}/block
Authorization: Bearer <token>
```

```http
POST /api/masters/{master_id}/unblock
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "message": "Мастер заблокирован"
}
```

### Удаление мастера
```http
DELETE /api/masters/{master_id}
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "message": "Мастер удален"
}
```

## 🔧 Управление категориями мастеров

### Обновление категорий мастера
```http
POST /api/masters/{master_id}/categories
Authorization: Bearer <token>
Content-Type: application/json
```

**Тело запроса:**
```json
{
  "categories": ["Электрика", "Сантехника"]
}
```

**Валидация:**
- Минимум 1 категория, максимум 10
- Категории должны быть из допустимого списка
- Дубликаты автоматически удаляются
- Пустые строки игнорируются

**Кэширование:**
- Категории мастера кэшируются в Redis на 1 час
- При обновлении кэш автоматически инвалидируется
- Общий кэш всех мастеров инвалидируется

**Ответ:**
```json
{
  "categories": ["Электрика", "Сантехника"],
  "master_id": 1,
  "updated_at": "2025-01-01T12:00:00"
}
```

### Кэширование данных

#### Категории мастеров
- **Ключ:** `master:categories:{master_id}`
- **TTL:** 3600 секунд (1 час)
- **Инвалидация:** При обновлении категорий

#### Статистика мастеров
- **Ключ:** `master:stats:{master_id}`
- **TTL:** 900 секунд (15 минут)
- **Инвалидация:** При изменении заказов

#### Общий кэш всех мастеров
- **Ключ:** `masters:categories:all`
- **TTL:** 1800 секунд (30 минут)
- **Инвалидация:** При любом изменении категорий

### Логи API запросов
Все API запросы логируются со следующей информацией:
- `master_id`: ID мастера
- `admin_username`: Имя администратора
- `user_agent`: User-Agent запроса
- `timestamp`: Время запроса
- `categories_count`: Количество категорий (для запросов обновления)

## 🚨 Обработка ошибок

### Валидация данных
```json
{
  "detail": [
    {
      "loc": ["body", "categories"],
      "msg": "Недопустимые категории: Неверная категория",
      "type": "value_error"
    }
  ]
}
```

### Авторизация
```json
{
  "detail": "Not authenticated"
}
```

### Не найдено
```json
{
  "detail": "Мастер не найден"
}
```

### Серверная ошибка
```json
{
  "detail": "Внутренняя ошибка сервера при обновлении категорий"
}
```

## 🛠️ Скрипты управления

### Управление администраторами
```bash
# Просмотр списка администраторов
python scripts/admin_management.py --list

# Создание администратора
python scripts/admin_management.py create newadmin newpass123 --email admin@example.com

# Изменение пароля
python scripts/admin_management.py password admin newpassword123

# Включение/выключение администратора
python scripts/admin_management.py toggle admin

# Для Docker окружения
python scripts/admin_management.py --docker --list
```

## 🧪 Тестирование

### Запуск тестов
```bash
# Все тесты
pytest

# Тесты API
pytest tests/test_api_categories_validation.py -v

# Тесты валидации
pytest tests/test_schemas_validation.py -v

# Тесты управления админами
pytest tests/test_admin_management.py -v
```

### Покрытие тестами
```bash
pytest --cov=admin --cov-report=html
```

## 🔧 Разработка

### Структура проекта
```
goodrobot/
├── admin/                 # Админ-панель
│   ├── app/
│   │   ├── routers/      # API роутеры
│   │   ├── schemas/      # Pydantic схемы
│   │   └── templates/    # Jinja2 шаблоны
│   └── static/           # Статические файлы
├── app/                  # Основное приложение
│   ├── models/           # SQLAlchemy модели
│   ├── bot/              # Telegram бот
│   └── core/             # Конфигурация
├── tests/                # Тесты
└── scripts/              # Скрипты управления
```

### Добавление новой категории
1. Обновить список в `app/models/category.py`
2. Перезапустить приложение
3. Категория автоматически станет доступной в API

---

## 📞 Поддержка
При возникновении вопросов обращайтесь к документации или создавайте issue в репозитории.