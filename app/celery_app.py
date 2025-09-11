from celery import Celery

from core.config import get_settings

settings = get_settings()

# Определяем URL брокера и бэкенда результатов
broker_url = settings.celery_broker_url or f"redis://{settings.redis_host}:{settings.redis_port}/0"
result_backend = settings.celery_result_backend or f"redis://{settings.redis_host}:{settings.redis_port}/1"

# Создаем экземпляр Celery
celery_app = Celery(
    'goodrobot',
    broker=broker_url,
    backend=result_backend,
    include=['app.tasks']  # Здесь будут находиться наши задачи
)

# Настройки Celery
celery_app.conf.update(
    # Настройки брокера и бэкенда
    broker_url=broker_url,
    result_backend=result_backend,

    # Настройки задач
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Almaty',
    enable_utc=True,

    # Настройки воркера
    worker_prefetch_multiplier=1,  # Предотвращает захват слишком большого количества задач
    task_acks_late=True,  # Подтверждение задачи только после успешного выполнения

    # Настройки повторных попыток
    task_default_retry_delay=60,  # 1 минута между повторными попытками
    task_max_retries=3,  # Максимальное количество повторных попыток

    # Настройки для отслеживания задач
    task_track_started=True,
)

# Если запускается как основной модуль
if __name__ == '__main__':
    celery_app.start()
