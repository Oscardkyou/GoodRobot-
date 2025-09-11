import json
import logging
from typing import Any

# Импорт Redis отключен временно
# from redis import asyncio as aioredis

from core.config import get_settings

# Получаем настройки
settings = get_settings()

logger = logging.getLogger(__name__)

# Заглушка вместо подключения к Redis
class RedisMock:
    """Заглушка для Redis при отсутствии подключения"""
    async def get(self, key):
        logger.warning(f"Redis отключен: попытка получить ключ {key}")
        return None
        
    async def set(self, key, value, ex=None):
        logger.warning(f"Redis отключен: попытка установить ключ {key}")
        return True
        
    async def delete(self, key):
        logger.warning(f"Redis отключен: попытка удалить ключ {key}")
        return True

# Используем заглушку вместо реального подключения
redis = RedisMock()

async def get_redis_connection():
    """Получение соединения с Redis (заглушка)"""
    logger.warning("Redis отключен: возвращаем заглушку вместо соединения")
    return redis

async def set_key(key: str, value: Any, expire: int | None = None) -> bool:
    """
    Установка значения в Redis с опциональным временем жизни (заглушка)
    
    Args:
        key: Ключ
        value: Значение (будет сериализовано в JSON)
        expire: Время жизни в секундах (None - бессрочно)
    
    Returns:
        bool: Успешность операции
    """
    try:
        logger.info(f"Redis отключен: имитация установки ключа {key}")
        return True
    except Exception as e:
        logger.error(f"Redis set error: {e}")
        return False

async def get_key(key: str, default: Any = None) -> Any:
    """
    Получение значения из Redis (заглушка)
    
    Args:
        key: Ключ
        default: Значение по умолчанию
    
    Returns:
        Any: Значение или default, если ключ не найден
    """
    try:
        logger.info(f"Redis отключен: имитация получения ключа {key}, возвращаем значение по умолчанию")
        return default
    except Exception as e:
        logger.error(f"Redis get error: {e}")
        return default

async def delete_key(key: str) -> bool:
    """
    Удаление ключа из Redis (заглушка)
    
    Args:
        key: Ключ для удаления
    
    Returns:
        bool: Успешность операции
    """
    try:
        logger.info(f"Redis отключен: имитация удаления ключа {key}")
        return True
    except Exception as e:
        logger.error(f"Redis delete error: {e}")
        return False

async def set_cache(key: str, value: Any, expire: int = 3600) -> bool:
    """
    Установка значения в кэш с временем жизни
    
    Args:
        key: Ключ кэша
        value: Значение для кэширования
        expire: Время жизни в секундах (по умолчанию 1 час)
    
    Returns:
        bool: Успешность операции
    """
    cache_key = f"cache:{key}"
    return await set_key(cache_key, value, expire)

async def get_cache(key: str, default: Any = None) -> Any:
    """
    Получение значения из кэша
    
    Args:
        key: Ключ кэша
        default: Значение по умолчанию
    
    Returns:
        Any: Закэшированное значение или default
    """
    cache_key = f"cache:{key}"
    return await get_key(cache_key, default)

async def invalidate_cache(key: str) -> bool:
    """
    Инвалидация кэша
    
    Args:
        key: Ключ кэша для инвалидации
    
    Returns:
        bool: Успешность операции
    """
    cache_key = f"cache:{key}"
    return await delete_key(cache_key)
