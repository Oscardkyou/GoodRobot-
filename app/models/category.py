"""SQLAlchemy model for master categories."""
from sqlalchemy import Column, ForeignKey, Integer, String, Table

from app.models.base import Base

# Таблица связи между мастерами и категориями (many-to-many)
master_categories = Table(
    "master_categories",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("category", String, primary_key=True),
)


class MasterCategory:
    """Вспомогательный класс для работы с категориями мастера.
    
    Не является моделью SQLAlchemy, а просто предоставляет
    константы и методы для работы с категориями.
    """

    # Список доступных категорий
    CATEGORIES = [
        "Электрика",
        "Сантехника",
        "Бытовая техника",
        "Клининг",
        "Строительные работы",
    ]

    @classmethod
    def get_all_categories(cls):
        """Возвращает список всех доступных категорий."""
        return cls.CATEGORIES
