"""
Сервис кэширования для категорий мастеров
"""

import logging
from typing import Any

from core.redis import get_cache, get_redis_connection, invalidate_cache, set_cache

logger = logging.getLogger(__name__)


class MasterCategoriesCache:
    """Сервис кэширования для категорий мастеров (заглушка без Redis)"""

    CACHE_TTL = 3600  # 1 час
    MASTER_CATEGORIES_PREFIX = "master:categories"
    ALL_MASTERS_CATEGORIES_PREFIX = "masters:categories:all"
    
    # Локальный кэш в памяти для имитации работы Redis
    _memory_cache = {}

    def __init__(self):
        self.redis = None

    async def _get_redis(self):
        """Получение соединения Redis (заглушка)"""
        if self.redis is None:
            self.redis = await get_redis_connection()
        return self.redis

    async def get_master_categories(self, master_id: int) -> list[str] | None:
        """
        Получение категорий мастера из кэша (заглушка)

        Args:
            master_id: ID мастера

        Returns:
            Optional[List[str]]: Список категорий или None если не найдено в кэше
        """
        try:
            cache_key = f"{self.MASTER_CATEGORIES_PREFIX}:{master_id}"
            # Используем локальный кэш вместо Redis
            categories = self._memory_cache.get(cache_key)
            
            if categories:
                logger.info(f"Memory cache hit for master {master_id} categories", extra={
                    "master_id": master_id,
                    "categories_count": len(categories) if categories else 0
                })
                return categories
            else:
                logger.info(f"Memory cache miss for master {master_id} categories", extra={
                    "master_id": master_id
                })
                return None

        except Exception as e:
            logger.error("Error getting master categories from memory cache", extra={
                "master_id": master_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            return None

    async def set_master_categories(self, master_id: int, categories: list[str]) -> bool:
        """
        Сохранение категорий мастера в кэш (заглушка)

        Args:
            master_id: ID мастера
            categories: Список категорий

        Returns:
            bool: Успешность операции
        """
        try:
            cache_key = f"{self.MASTER_CATEGORIES_PREFIX}:{master_id}"

            # Сохраняем в локальный кэш вместо Redis
            self._memory_cache[cache_key] = categories
            success = True

            if success:
                logger.info(f"Successfully cached categories for master {master_id} in memory", extra={
                    "master_id": master_id,
                    "categories_count": len(categories),
                    "cache_key": cache_key
                })

                # Также инвалидируем кэш всех мастеров
                await self.invalidate_all_masters_categories_cache()
            else:
                logger.warning(f"Failed to cache categories for master {master_id} in memory", extra={
                    "master_id": master_id,
                    "categories_count": len(categories)
                })

            return success

        except Exception as e:
            logger.error("Error setting master categories to memory cache", extra={
                "master_id": master_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            return False

    async def invalidate_master_categories_cache(self, master_id: int) -> bool:
        """
        Инвалидация кэша категорий мастера (заглушка)

        Args:
            master_id: ID мастера

        Returns:
            bool: Успешность операции
        """
        try:
            cache_key = f"{self.MASTER_CATEGORIES_PREFIX}:{master_id}"

            # Удаляем из локального кэша
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]
            success = True

            if success:
                logger.info(f"Successfully invalidated memory cache for master {master_id}", extra={
                    "master_id": master_id,
                    "cache_key": cache_key
                })
            else:
                logger.warning(f"Failed to invalidate memory cache for master {master_id}", extra={
                    "master_id": master_id
                })

            return success

        except Exception as e:
            logger.error("Error invalidating master categories memory cache", extra={
                "master_id": master_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            return False

    async def get_all_masters_categories(self) -> dict[int, list[str]] | None:
        """
        Получение категорий всех мастеров из кэша (заглушка)

        Returns:
            Optional[Dict[int, List[str]]]: Словарь {master_id: categories} или None
        """
        try:
            # Получаем из локального кэша
            categories = self._memory_cache.get(self.ALL_MASTERS_CATEGORIES_PREFIX)

            if categories:
                logger.info("Memory cache hit for all masters categories", extra={
                    "masters_count": len(categories) if categories else 0
                })
                return categories
            else:
                logger.info("Memory cache miss for all masters categories")
                return None

        except Exception as e:
            logger.error("Error getting all masters categories from memory cache", extra={
                "error": str(e),
                "error_type": type(e).__name__
            })
            return None

    async def set_all_masters_categories(self, all_categories: dict[int, list[str]]) -> bool:
        """
        Сохранение категорий всех мастеров в кэш (заглушка)

        Args:
            all_categories: Словарь {master_id: categories}

        Returns:
            bool: Успешность операции
        """
        try:
            # Сохраняем в локальный кэш
            self._memory_cache[self.ALL_MASTERS_CATEGORIES_PREFIX] = all_categories
            success = True

            if success:
                logger.info("Successfully cached all masters categories in memory", extra={
                    "masters_count": len(all_categories),
                    "cache_key": self.ALL_MASTERS_CATEGORIES_PREFIX
                })
            else:
                logger.warning("Failed to cache all masters categories in memory")

            return success

        except Exception as e:
            logger.error("Error setting all masters categories to memory cache", extra={
                "error": str(e),
                "error_type": type(e).__name__
            })
            return False

    async def invalidate_all_masters_categories_cache(self) -> bool:
        """
        Инвалидация кэша всех категорий мастеров (заглушка)

        Returns:
            bool: Успешность операции
        """
        try:
            # Удаляем из локального кэша
            if self.ALL_MASTERS_CATEGORIES_PREFIX in self._memory_cache:
                del self._memory_cache[self.ALL_MASTERS_CATEGORIES_PREFIX]
            success = True

            if success:
                logger.info("Successfully invalidated all masters categories memory cache", extra={
                    "cache_key": self.ALL_MASTERS_CATEGORIES_PREFIX
                })
            else:
                logger.warning("Failed to invalidate all masters categories memory cache")

            return success

        except Exception as e:
            logger.error("Error invalidating all masters categories memory cache", extra={
                "error": str(e),
                "error_type": type(e).__name__
            })
            return False

    async def get_master_stats(self, master_id: int) -> dict[str, Any] | None:
        """
        Получение статистики мастера из кэша (заглушка)

        Args:
            master_id: ID мастера

        Returns:
            Optional[Dict[str, Any]]: Статистика мастера или None
        """
        try:
            cache_key = f"master:stats:{master_id}"
            # Получаем из локального кэша
            stats = self._memory_cache.get(cache_key)

            if stats:
                logger.info(f"Memory cache hit for master {master_id} stats", extra={
                    "master_id": master_id
                })
                return stats
            else:
                logger.info(f"Memory cache miss for master {master_id} stats", extra={
                    "master_id": master_id
                })
                return None

        except Exception as e:
            logger.error("Error getting master stats from memory cache", extra={
                "master_id": master_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            return None

    async def set_master_stats(self, master_id: int, stats: dict[str, Any]) -> bool:
        """
        Сохранение статистики мастера в кэш (заглушка)

        Args:
            master_id: ID мастера
            stats: Статистика мастера

        Returns:
            bool: Успешность операции
        """
        try:
            cache_key = f"master:stats:{master_id}"

            # Сохраняем в локальный кэш
            self._memory_cache[cache_key] = stats
            success = True

            if success:
                logger.info(f"Successfully cached stats for master {master_id} in memory", extra={
                    "master_id": master_id,
                    "cache_key": cache_key
                })
            else:
                logger.warning(f"Failed to cache stats for master {master_id} in memory", extra={
                    "master_id": master_id
                })

            return success

        except Exception as e:
            logger.error("Error setting master stats to memory cache", extra={
                "master_id": master_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            return False

    async def invalidate_master_stats_cache(self, master_id: int) -> bool:
        """
        Инвалидация кэша статистики мастера (заглушка)

        Args:
            master_id: ID мастера

        Returns:
            bool: Успешность операции
        """
        try:
            cache_key = f"master:stats:{master_id}"

            # Удаляем из локального кэша
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]
            success = True

            if success:
                logger.info(f"Successfully invalidated stats memory cache for master {master_id}", extra={
                    "master_id": master_id,
                    "cache_key": cache_key
                })
            else:
                logger.warning(f"Failed to invalidate stats memory cache for master {master_id}", extra={
                    "master_id": master_id
                })

            return success

        except Exception as e:
            logger.error("Error invalidating master stats memory cache", extra={
                "master_id": master_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            return False


# Глобальный экземпляр сервиса кэширования
master_categories_cache = MasterCategoriesCache()


async def get_master_categories_cache() -> MasterCategoriesCache:
    """Получение экземпляра сервиса кэширования"""
    return master_categories_cache
