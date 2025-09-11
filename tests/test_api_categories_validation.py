"""
Тесты для API эндпоинтов управления категориями мастеров с новой валидацией
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from admin.app.schemas_category import MasterCategoryResponse, MasterCategoryUpdate
from app.models.user import User


class TestMasterCategoriesAPI:
    """Тесты для API управления категориями мастеров"""

    @pytest.fixture
    def mock_master(self):
        """Фикстура для мока мастера"""
        master = AsyncMock(spec=User)
        master.id = 1
        master.name = "Test Master"
        master.role = "master"
        master.categories = ["Электрика", "Сантехника"]
        return master

    @pytest.fixture
    def mock_admin(self):
        """Фикстура для мока администратора"""
        admin = AsyncMock(spec=User)
        admin.id = 2
        admin.username = "admin"
        admin.role = "admin"
        admin.is_active = True
        return admin

    @pytest.fixture
    def valid_categories_data(self):
        """Фикстура с валидными данными категорий"""
        return MasterCategoryUpdate(categories=["Электрика", "Сантехника"])

    @pytest.fixture
    def invalid_categories_data(self):
        """Фикстура с невалидными данными категорий"""
        return {"categories": ["Электрика", "Недопустимая категория"]}

    @pytest.mark.asyncio
    async def test_update_categories_success(self, mock_master, mock_admin, valid_categories_data):
        """Тест успешного обновления категорий"""
        from admin.app.routers.masters import update_master_categories

        mock_session = AsyncMock(spec=AsyncSession)

        # Мокаем запрос к БД
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_master
        mock_session.execute.return_value = mock_result

        # Мокаем зависимости
        with patch('admin.app.routers.masters.get_session') as mock_get_session, \
             patch('admin.app.routers.masters.datetime') as mock_datetime:

            mock_get_session.return_value = mock_session
            mock_datetime.now.return_value.isoformat.return_value = "2025-01-01T12:00:00"

            # Вызываем функцию
            response = await update_master_categories(
                master_id=1,
                categories=valid_categories_data,
                db=mock_session,
                current_admin=mock_admin
            )

            # Проверяем результат
            assert isinstance(response, MasterCategoryResponse)
            assert response.master_id == 1
            assert response.categories == ["Электрика", "Сантехника"]
            assert response.updated_at == "2025-01-01T12:00:00"

    @pytest.mark.asyncio
    async def test_update_categories_master_not_found(self, mock_admin):
        """Тест обновления категорий для несуществующего мастера"""
        from admin.app.routers.masters import update_master_categories

        mock_session = AsyncMock(spec=AsyncSession)

        # Мокаем запрос к БД (мастер не найден)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch('admin.app.routers.masters.get_session') as mock_get_session:
            mock_get_session.return_value = mock_session

            # Вызываем функцию и ожидаем исключение
            with pytest.raises(HTTPException) as exc_info:
                await update_master_categories(
                    master_id=999,
                    categories=MasterCategoryUpdate(categories=["Электрика"]),
                    db=mock_session,
                    current_admin=mock_admin
                )

            assert exc_info.value.status_code == 404
            assert "Мастер не найден" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_categories_validation_error(self, mock_master, mock_admin, invalid_categories_data):
        """Тест валидации данных при обновлении категорий"""

        # Создаем невалидные данные (это вызовет ValidationError)
        with pytest.raises(Exception):  # Pydantic ValidationError
            invalid_update = MasterCategoryUpdate(**invalid_categories_data)

    @pytest.mark.asyncio
    async def test_update_categories_database_error(self, mock_master, mock_admin, valid_categories_data):
        """Тест обработки ошибок базы данных"""
        from admin.app.routers.masters import update_master_categories

        mock_session = AsyncMock(spec=AsyncSession)

        # Мокаем запрос к БД с ошибкой
        mock_session.execute.side_effect = Exception("Database connection error")

        with patch('admin.app.routers.masters.get_session') as mock_get_session:
            mock_get_session.return_value = mock_session

            # Вызываем функцию и ожидаем исключение
            with pytest.raises(HTTPException) as exc_info:
                await update_master_categories(
                    master_id=1,
                    categories=valid_categories_data,
                    db=mock_session,
                    current_admin=mock_admin
                )

            assert exc_info.value.status_code == 500
            assert "Внутренняя ошибка сервера" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_categories_logging(self, mock_master, mock_admin, valid_categories_data):
        """Тест логирования при обновлении категорий"""
        from admin.app.routers.masters import update_master_categories

        mock_session = AsyncMock(spec=AsyncSession)

        # Мокаем запрос к БД
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_master
        mock_session.execute.return_value = mock_result

        with patch('admin.app.routers.masters.get_session') as mock_get_session, \
             patch('admin.app.routers.masters.logger') as mock_logger, \
             patch('admin.app.routers.masters.datetime') as mock_datetime:

            mock_get_session.return_value = mock_session
            mock_datetime.now.return_value.isoformat.return_value = "2025-01-01T12:00:00"

            # Вызываем функцию
            await update_master_categories(
                master_id=1,
                categories=valid_categories_data,
                db=mock_session,
                current_admin=mock_admin
            )

            # Проверяем логирование
            mock_logger.info.assert_called()
            assert mock_logger.info.call_count >= 2  # info + success logs

    def test_response_schema_structure(self):
        """Тест структуры схемы ответа"""
        response = MasterCategoryResponse(
            categories=["Электрика", "Сантехника"],
            master_id=1,
            updated_at="2025-01-01T12:00:00"
        )

        # Проверяем структуру
        assert hasattr(response, 'categories')
        assert hasattr(response, 'master_id')
        assert hasattr(response, 'updated_at')

        # Проверяем типы
        assert isinstance(response.categories, list)
        assert isinstance(response.master_id, int)
        assert isinstance(response.updated_at, str)


class TestCategoriesValidationEdgeCases:
    """Тесты граничных случаев валидации"""

    def test_category_name_edge_cases(self):
        """Тест граничных случаев названий категорий"""
        # Максимально допустимая длина
        max_length_category = "А" * 50
        update = MasterCategoryUpdate(categories=[max_length_category])
        assert update.categories == [max_length_category]

        # Слишком длинное название
        too_long_category = "А" * 51
        with pytest.raises(Exception):
            MasterCategoryUpdate(categories=[too_long_category])

    def test_empty_and_whitespace_categories(self):
        """Тест обработки пустых и пробельных категорий"""
        # Категории с пробелами
        update = MasterCategoryUpdate(categories=["  Электрика  ", " Сантехника ", "   "])
        assert update.categories == ["Электрика", "Сантехника"]

        # Только пустые категории
        with pytest.raises(Exception):
            MasterCategoryUpdate(categories=["   ", ""])

    def test_max_categories_limit(self):
        """Тест ограничения на максимальное количество категорий"""
        # Максимально допустимое количество
        categories = ["Категория"] * 10
        update = MasterCategoryUpdate(categories=categories)
        assert len(update.categories) == 10

        # Превышение лимита
        too_many_categories = ["Категория"] * 11
        with pytest.raises(Exception):
            MasterCategoryUpdate(categories=too_many_categories)
