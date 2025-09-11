"""
Тесты для улучшенных схем валидации категорий мастеров
"""

import pytest
from pydantic import ValidationError

from admin.app.schemas_category import MasterCategoryResponse, MasterCategoryUpdate


class TestMasterCategoryUpdate:
    """Тесты для схемы MasterCategoryUpdate"""

    def test_valid_categories(self):
        """Тест валидных категорий"""
        update = MasterCategoryUpdate(categories=["Электрика", "Сантехника"])
        assert update.categories == ["Электрика", "Сантехника"]

    def test_empty_categories_list(self):
        """Тест пустого списка категорий"""
        with pytest.raises(ValidationError) as exc_info:
            MasterCategoryUpdate(categories=[])
        assert "Список категорий не может быть пустым" in str(exc_info.value)

    def test_too_many_categories(self):
        """Тест превышения максимального количества категорий"""
        categories = ["Категория"] * 15  # 15 > 10
        with pytest.raises(ValidationError) as exc_info:
            MasterCategoryUpdate(categories=categories)
        assert "should have at most 10 items" in str(exc_info.value)

    def test_duplicate_categories_removed(self):
        """Тест удаления дубликатов"""
        update = MasterCategoryUpdate(
            categories=["Электрика", "Сантехника", "Электрика", "Сантехника"]
        )
        assert update.categories == ["Электрика", "Сантехника"]

    def test_whitespace_handling(self):
        """Тест обработки пробелов в названиях"""
        update = MasterCategoryUpdate(
            categories=["  Электрика  ", " Сантехника ", "   ", "Бытовая техника"]
        )
        assert update.categories == ["Электрика", "Сантехника", "Бытовая техника"]

    def test_invalid_category_type(self):
        """Тест невалидного типа данных"""
        with pytest.raises(ValidationError) as exc_info:
            MasterCategoryUpdate(categories=["Электрика", 123, "Сантехника"])
        assert "Все категории должны быть строками" in str(exc_info.value)

    def test_category_too_long(self):
        """Тест слишком длинного названия категории"""
        long_category = "А" * 51  # 51 > 50
        with pytest.raises(ValidationError) as exc_info:
            MasterCategoryUpdate(categories=[long_category])
        assert "не может быть длиннее 50 символов" in str(exc_info.value)

    def test_invalid_category_name(self):
        """Тест недопустимого названия категории"""
        with pytest.raises(ValidationError) as exc_info:
            MasterCategoryUpdate(categories=["Недопустимая категория"])
        assert "Недопустимые категории" in str(exc_info.value)

    def test_mixed_valid_invalid_categories(self):
        """Тест смеси валидных и невалидных категорий"""
        with pytest.raises(ValidationError) as exc_info:
            MasterCategoryUpdate(categories=["Электрика", "Недопустимая", "Сантехника"])
        assert "Недопустимые категории" in str(exc_info.value)


class TestMasterCategoryResponse:
    """Тесты для схемы MasterCategoryResponse"""

    def test_valid_response(self):
        """Тест валидного ответа"""
        response = MasterCategoryResponse(
            categories=["Электрика", "Сантехника"],
            master_id=1,
            updated_at="2025-01-01T12:00:00"
        )
        assert response.categories == ["Электрика", "Сантехника"]
        assert response.master_id == 1
        assert response.updated_at == "2025-01-01T12:00:00"

    def test_empty_categories_response(self):
        """Тест ответа с пустыми категориями"""
        response = MasterCategoryResponse(
            categories=[],
            master_id=1,
            updated_at="2025-01-01T12:00:00"
        )
        assert response.categories == []

    def test_missing_required_field(self):
        """Тест отсутствия обязательного поля"""
        with pytest.raises(ValidationError):
            MasterCategoryResponse(
                categories=["Электрика"],
                # master_id отсутствует
                updated_at="2025-01-01T12:00:00"
            )


class TestCategoryValidationIntegration:
    """Интеграционные тесты валидации"""

    @pytest.fixture
    def valid_categories_data(self):
        """Фикстура с валидными данными"""
        return {
            "categories": ["Электрика", "Сантехника", "Бытовая техника"]
        }

    @pytest.fixture
    def invalid_categories_data(self):
        """Фикстура с невалидными данными"""
        return {
            "categories": ["Электрика", "Недопустимая категория"]
        }

    def test_successful_validation_pipeline(self, valid_categories_data):
        """Тест полной цепочки валидации с валидными данными"""
        update = MasterCategoryUpdate(**valid_categories_data)
        assert len(update.categories) == 3
        assert "Электрика" in update.categories

    def test_validation_error_pipeline(self, invalid_categories_data):
        """Тест полной цепочки валидации с невалидными данными"""
        with pytest.raises(ValidationError) as exc_info:
            MasterCategoryUpdate(**invalid_categories_data)

        # Проверяем, что ошибка содержит информацию о недопустимых категориях
        error_detail = str(exc_info.value)
        assert "Недопустимые категории" in error_detail
        assert "Недопустимая категория" in error_detail

    def test_response_creation_from_update(self, valid_categories_data):
        """Тест создания ответа на основе обновления"""
        update = MasterCategoryUpdate(**valid_categories_data)

        response = MasterCategoryResponse(
            categories=update.categories,
            master_id=123,
            updated_at="2025-01-01T12:00:00"
        )

        assert response.categories == update.categories
        assert response.master_id == 123
