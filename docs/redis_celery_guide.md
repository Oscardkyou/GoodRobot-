# Руководство по использованию Redis и Celery в проекте GoodRobot

## Содержание
1. [Введение](#введение)
2. [Redis](#redis)
   - [Основные сценарии использования](#основные-сценарии-использования-redis)
   - [Работа с модулем Redis](#работа-с-модулем-redis)
3. [Celery](#celery)
   - [Архитектура Celery в проекте](#архитектура-celery-в-проекте)
   - [Создание и запуск задач](#создание-и-запуск-задач)
   - [Мониторинг задач](#мониторинг-задач)
4. [Примеры использования](#примеры-использования)
   - [Кэширование данных](#кэширование-данных)
   - [Фоновые задачи](#фоновые-задачи)
   - [Отложенные уведомления](#отложенные-уведомления)

## Введение

В проект GoodRobot добавлены Redis и Celery для улучшения производительности и обеспечения асинхронной обработки задач. Redis используется как кэш и брокер сообщений для Celery, а Celery позволяет выполнять длительные операции в фоновом режиме.

## Redis

### Основные сценарии использования Redis

1. **Кэширование данных**
   - Кэширование результатов запросов к базе данных
   - Хранение временных данных с TTL (time-to-live)
   - Кэширование сессий пользователей

2. **Rate limiting**
   - Ограничение количества запросов от пользователей
   - Защита от DDoS-атак

3. **Хранение состояний**
   - Хранение временных состояний пользователей
   - Хранение данных для восстановления после сбоев

### Работа с модулем Redis

Для работы с Redis в проекте используется модуль `core.redis`. Основные функции:

```python
# Получение соединения с Redis
redis = await get_redis_connection()

# Установка значения с опциональным TTL
await set_key("key", "value", expire=3600)  # expire в секундах

# Получение значения
value = await get_key("key", default="default_value")

# Удаление ключа
await delete_key("key")

# Работа с кэшем
await set_cache("user:123", user_data, expire=3600)
user_data = await get_cache("user:123")
await invalidate_cache("user:123")
```

## Celery

### Архитектура Celery в проекте

Celery в проекте GoodRobot настроен следующим образом:
- **Брокер**: Redis (для очередей задач)
- **Бэкенд результатов**: Redis (для хранения результатов выполнения задач)
- **Воркеры**: Контейнер `celery_worker` в Docker Compose

### Создание и запуск задач

Для создания новой задачи используйте декоратор `@shared_task` или `@celery_app.task`:

```python
from app.celery_app import celery_app
from celery import shared_task

@shared_task(bind=True, name="my_task")
def my_task(self, param1, param2):
    # Логика задачи
    return {"result": "success"}
```

Для запуска задачи:

```python
# Асинхронный запуск (не ждем результата)
my_task.delay(param1, param2)

# Асинхронный запуск с дополнительными параметрами
my_task.apply_async(
    args=[param1, param2],
    countdown=60,  # Запуск через 60 секунд
    expires=3600,  # Задача истекает через 3600 секунд
    retry=True,    # Автоматический повтор при ошибке
    retry_policy={
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.5,
    }
)
```

### Мониторинг задач

Для мониторинга задач можно использовать Flower - веб-интерфейс для Celery:

```bash
celery -A app.celery_app flower --port=5555
```

Или добавить в docker-compose.yml:

```yaml
flower:
  build: .
  command: celery -A app.celery_app flower --port=5555
  ports:
    - "5555:5555"
  depends_on:
    - redis
    - celery_worker
  env_file:
    - .env
  volumes:
    - .:/app
```

## Примеры использования

### Кэширование данных

```python
from core.redis import get_cache, set_cache
from app.models.user import User
from sqlalchemy.future import select

async def get_user_by_id(user_id: int, db):
    # Пробуем получить из кэша
    cache_key = f"user:{user_id}"
    user_data = await get_cache(cache_key)
    
    if user_data:
        return user_data
    
    # Если нет в кэше, получаем из БД
    query = select(User).filter(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user:
        # Сериализуем и кэшируем на 1 час
        user_dict = user.to_dict()
        await set_cache(cache_key, user_dict, expire=3600)
        return user_dict
    
    return None
```

### Фоновые задачи

```python
from app.tasks import process_bid_assignment

# В обработчике API
@router.post("/bids/{bid_id}/assign")
async def assign_bid_to_master(
    bid_id: int,
    master_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Проверка существования заявки и мастера
    # ...
    
    # Запуск фоновой задачи
    process_bid_assignment.delay(bid_id, master_id)
    
    return {"status": "processing"}
```

### Отложенные уведомления

```python
from app.tasks import send_notification
from datetime import datetime, timedelta

# Отправка уведомления через 1 час
send_time = datetime.utcnow() + timedelta(hours=1)

send_notification.apply_async(
    args=[user_id, "Напоминаем о вашей заявке"],
    eta=send_time
)
```
