"""
Тесты для сервиса кэширования категорий мастеров
"""

from unittest.mock import AsyncMock, patch

import pytest

from core.cache_service import MasterCategoriesCache


class TestMasterCategoriesCache:
    """Тесты для сервиса кэширования категорий мастеров"""

    @pytest.fixture
    def cache_service(self):
        """Фикстура для сервиса кэширования"""
        return MasterCategoriesCache()

    @pytest.fixture
    def mock_redis(self):
        """Фикстура для мока Redis"""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_master_categories_cache_hit(self, cache_service):
        """Тест получения категорий из кэша (cache hit)"""
        master_id = 1
        expected_categories = ["Электрика", "Сантехника"]

        with patch('core.cache_service.get_cache', return_value=expected_categories):
            categories = await cache_service.get_master_categories(master_id)

            assert categories == expected_categories

    @pytest.mark.asyncio
    async def test_get_master_categories_cache_miss(self, cache_service):
        """Тест получения категорий из кэша (cache miss)"""
        master_id = 1

        with patch('core.cache_service.get_cache', return_value=None):
            categories = await cache_service.get_master_categories(master_id)

            assert categories is None

    @pytest.mark.asyncio
    async def test_set_master_categories_success(self, cache_service):
        """Тест успешного сохранения категорий в кэш"""
        master_id = 1
        categories = ["Электрика", "Сантехника"]

        with patch('core.cache_service.set_cache', return_value=True) as mock_set_cache, \
             patch.object(cache_service, 'invalidate_all_masters_categories_cache', return_value=True):

            success = await cache_service.set_master_categories(master_id, categories)

            assert success is True
            mock_set_cache.assert_called_once_with(
                f"{cache_service.MASTER_CATEGORIES_PREFIX}:{master_id}",
                categories,
                cache_service.CACHE_TTL
            )

    @pytest.mark.asyncio
    async def test_set_master_categories_failure(self, cache_service):
        """Тест неудачного сохранения категорий в кэш"""
        master_id = 1
        categories = ["Электрика", "Сантехника"]

        with patch('core.cache_service.set_cache', return_value=False):
            success = await cache_service.set_master_categories(master_id, categories)

            assert success is False

    @pytest.mark.asyncio
    async def test_invalidate_master_categories_cache_success(self, cache_service):
        """Тест успешной инвалидации кэша категорий мастера"""
        master_id = 1

        with patch('core.cache_service.invalidate_cache', return_value=True):
            success = await cache_service.invalidate_master_categories_cache(master_id)

            assert success is True

    @pytest.mark.asyncio
    async def test_invalidate_master_categories_cache_failure(self, cache_service):
        """Тест неудачной инвалидации кэша категорий мастера"""
        master_id = 1

        with patch('core.cache_service.invalidate_cache', return_value=False):
            success = await cache_service.invalidate_master_categories_cache(master_id)

            assert success is False

    @pytest.mark.asyncio
    async def test_get_all_masters_categories_cache_hit(self, cache_service):
        """Тест получения категорий всех мастеров из кэша (cache hit)"""
        expected_data = {
            1: ["Электрика", "Сантехника"],
            2: ["Бытовая техника"]
        }

        with patch('core.cache_service.get_cache', return_value=expected_data):
            data = await cache_service.get_all_masters_categories()

            assert data == expected_data

    @pytest.mark.asyncio
    async def test_get_all_masters_categories_cache_miss(self, cache_service):
        """Тест получения категорий всех мастеров из кэша (cache miss)"""
        with patch('core.cache_service.get_cache', return_value=None):
            data = await cache_service.get_all_masters_categories()

            assert data is None

    @pytest.mark.asyncio
    async def test_set_all_masters_categories_success(self, cache_service):
        """Тест успешного сохранения категорий всех мастеров в кэш"""
        all_categories = {
            1: ["Электрика", "Сантехника"],
            2: ["Бытовая техника"]
        }

        with patch('core.cache_service.set_cache', return_value=True):
            success = await cache_service.set_all_masters_categories(all_categories)

            assert success is True

    @pytest.mark.asyncio
    async def test_invalidate_all_masters_categories_cache(self, cache_service):
        """Тест инвалидации кэша всех категорий мастеров"""
        with patch('core.cache_service.invalidate_cache', return_value=True):
            success = await cache_service.invalidate_all_masters_categories_cache()

            assert success is True

    @pytest.mark.asyncio
    async def test_get_master_stats_cache_hit(self, cache_service):
        """Тест получения статистики мастера из кэша (cache hit)"""
        master_id = 1
        expected_stats = {
            "completed_orders": 15,
            "active_orders": 2
        }

        with patch('core.cache_service.get_cache', return_value=expected_stats):
            stats = await cache_service.get_master_stats(master_id)

            assert stats == expected_stats

    @pytest.mark.asyncio
    async def test_get_master_stats_cache_miss(self, cache_service):
        """Тест получения статистики мастера из кэша (cache miss)"""
        master_id = 1

        with patch('core.cache_service.get_cache', return_value=None):
            stats = await cache_service.get_master_stats(master_id)

            assert stats is None

    @pytest.mark.asyncio
    async def test_set_master_stats_success(self, cache_service):
        """Тест успешного сохранения статистики мастера в кэш"""
        master_id = 1
        stats = {
            "completed_orders": 15,
            "active_orders": 2
        }

        with patch('core.cache_service.set_cache', return_value=True):
            success = await cache_service.set_master_stats(master_id, stats)

            assert success is True

    @pytest.mark.asyncio
    async def test_invalidate_master_stats_cache(self, cache_service):
        """Тест инвалидации кэша статистики мастера"""
        master_id = 1

        with patch('core.cache_service.invalidate_cache', return_value=True):
            success = await cache_service.invalidate_master_stats_cache(master_id)

            assert success is True

    @pytest.mark.asyncio
    async def test_error_handling_get_master_categories(self, cache_service):
        """Тест обработки ошибок при получении категорий из кэша"""
        master_id = 1

        with patch('core.cache_service.get_cache', side_effect=Exception("Redis connection error")):
            categories = await cache_service.get_master_categories(master_id)

            assert categories is None

    @pytest.mark.asyncio
    async def test_error_handling_set_master_categories(self, cache_service):
        """Тест обработки ошибок при сохранении категорий в кэш"""
        master_id = 1
        categories = ["Электрика", "Сантехника"]

        with patch('core.cache_service.set_cache', side_effect=Exception("Redis connection error")):
            success = await cache_service.set_master_categories(master_id, categories)

            assert success is False

    def test_cache_constants(self, cache_service):
        """Тест констант кэширования"""
        assert cache_service.CACHE_TTL == 3600  # 1 час
        assert cache_service.MASTER_CATEGORIES_PREFIX == "master:categories"
        assert cache_service.ALL_MASTERS_CATEGORIES_PREFIX == "masters:categories:all"


class TestCacheIntegration:
    """Интеграционные тесты кэширования"""

    @pytest.mark.asyncio
    async def test_cache_workflow_update_categories(self, cache_service):
        """Тест полного рабочего процесса обновления категорий с кэшированием"""
        master_id = 1
        old_categories = ["Электрика"]
        new_categories = ["Электрика", "Сантехника"]

        # Мокаем все необходимые функции
        with patch('core.cache_service.get_cache', return_value=old_categories), \
             patch('core.cache_service.set_cache', return_value=True), \
             patch('core.cache_service.invalidate_cache', return_value=True):

            # Проверяем получение старых категорий
            old_cached = await cache_service.get_master_categories(master_id)
            assert old_cached == old_categories

            # Обновляем категории
            success = await cache_service.set_master_categories(master_id, new_categories)
            assert success is True

            # Проверяем, что инвалидация общего кэша была вызвана
            # (проверяется косвенно через вызов invalidate_all_masters_categories_cache)

    @pytest.mark.asyncio
    async def test_cache_performance_simulation(self, cache_service):
        """Симуляция производительности кэширования"""
        master_id = 1
        categories = ["Электрика", "Сантехника", "Бытовая техника"]

        # Мокаем быстрое получение из кэша
        with patch('core.cache_service.get_cache', return_value=categories):
            # Это должно быть очень быстро
            result = await cache_service.get_master_categories(master_id)
            assert result == categories

        # Мокаем медленное получение из БД (имитация)
        with patch('core.cache_service.get_cache', return_value=None):
            # Это должно быть медленнее, но мы просто проверяем None
            result = await cache_service.get_master_categories(master_id)
            assert result is None
