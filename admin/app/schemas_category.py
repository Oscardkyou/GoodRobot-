
from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError


class MasterCategoryUpdate(BaseModel):
    """Схема для обновления категорий мастера с валидацией."""

    categories: list[str] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="Список категорий мастера (минимум 1, максимум 10)"
    )

    @field_validator('categories')
    @classmethod
    def validate_categories(cls, v: list[str]) -> list[str]:
        """Валидирует список категорий"""
        if not v:
            raise PydanticCustomError(
                'empty_categories',
                'Список категорий не может быть пустым'
            )

        # Убираем дубликаты и пустые строки
        unique_categories = []
        seen = set()

        for category in v:
            if not isinstance(category, str):
                raise PydanticCustomError(
                    'invalid_category_type',
                    'Все категории должны быть строками'
                )

            category = category.strip()
            if not category:
                continue  # Пропускаем пустые строки

            if len(category) > 50:
                raise PydanticCustomError(
                    'category_too_long',
                    'Название категории не может быть длиннее 50 символов'
                )

            if category in seen:
                continue  # Пропускаем дубликаты

            seen.add(category)
            unique_categories.append(category)

        if not unique_categories:
            raise PydanticCustomError(
                'no_valid_categories',
                'После валидации не осталось допустимых категорий'
            )

        return unique_categories

    @field_validator('categories')
    @classmethod
    def validate_allowed_categories(cls, v: list[str]) -> list[str]:
        """Проверяет, что все категории из допустимого списка"""
        from app.models.category import MasterCategory

        allowed_categories = MasterCategory.get_all_categories()
        invalid_categories = [cat for cat in v if cat not in allowed_categories]

        if invalid_categories:
            raise PydanticCustomError(
                'invalid_categories',
                'Недопустимые категории: {invalid}',
                {'invalid': ', '.join(invalid_categories)}
            )

        return v


class MasterCategoryResponse(BaseModel):
    """Схема для ответа с категориями мастера."""

    categories: list[str] = Field(
        ...,
        description="Текущие категории мастера"
    )
    master_id: int = Field(
        ...,
        description="ID мастера"
    )
    updated_at: str = Field(
        ...,
        description="Время последнего обновления"
    )
