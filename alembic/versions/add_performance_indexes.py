"""Add database indexes for performance optimization

Revision ID: add_performance_indexes
Revises: previous_revision_id
Create Date: 2025-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from alembic.context import get_context


# revision identifiers, used by Alembic.
revision = 'add_performance_indexes'
down_revision = None  # Root branch; merged later by 10cad352dcf7
branch_labels = None
depends_on = '5e736ec389db'  # Ensure specialties and master_specialties exist before creating their indexes

# Отключаем транзакционное выполнение для этой миграции
is_transactional = False


def upgrade():
    """Добавление индексов для оптимизации производительности"""
    
    # Получаем соединение напрямую, чтобы выполнять операции вне транзакции
    connection = op.get_bind()
    
    # Проверяем, существует ли уже запись о версии в alembic_version
    result = connection.execute(sa.text("SELECT EXISTS(SELECT 1 FROM alembic_version WHERE version_num = 'add_performance_indexes')")).scalar()
    if result:
        print("Миграция add_performance_indexes уже применена, пропускаем вставку версии")
        # Устанавливаем флаг, чтобы alembic не пытался вставить версию снова
        context = get_context()
        if hasattr(context, '_version_inserted'):
            context._version_inserted = True
    
    # Используем try-except для обработки случаев, когда индексы уже существуют
    
    # Индекс для быстрого поиска по роли пользователя
    try:
        connection.execute(sa.text("COMMIT"))
        op.create_index('ix_users_role', 'users', ['role'])
    except Exception as e:
        connection.execute(sa.text("ROLLBACK"))
        print(f"Индекс ix_users_role уже существует или другая ошибка: {e}")

    # Индекс для поиска активных/неактивных пользователей
    try:
        connection.execute(sa.text("COMMIT"))
        op.create_index('ix_users_is_active', 'users', ['is_active'])
    except Exception as e:
        connection.execute(sa.text("ROLLBACK"))
        print(f"Индекс ix_users_is_active уже существует или другая ошибка: {e}")

    # Составной индекс для поиска мастеров по статусу и ID
    try:
        connection.execute(sa.text("COMMIT"))
        op.create_index('ix_users_role_is_active', 'users', ['role', 'is_active'])
    except Exception as e:
        connection.execute(sa.text("ROLLBACK"))
        print(f"Индекс ix_users_role_is_active уже существует или другая ошибка: {e}")

    # Индекс для поиска по username (часто используется для аутентификации)
    try:
        connection.execute(sa.text("COMMIT"))
        op.create_index('ix_users_username', 'users', ['username'])
    except Exception as e:
        connection.execute(sa.text("ROLLBACK"))
        print(f"Индекс ix_users_username уже существует или другая ошибка: {e}")

    # Индекс для поиска по телефону
    try:
        connection.execute(sa.text("COMMIT"))
        op.create_index('ix_users_phone', 'users', ['phone'])
    except Exception as e:
        connection.execute(sa.text("ROLLBACK"))
        print(f"Индекс ix_users_phone уже существует или другая ошибка: {e}")

    # Индекс для поиска по Telegram ID
    try:
        connection.execute(sa.text("COMMIT"))
        op.create_index('ix_users_tg_id', 'users', ['tg_id'])
    except Exception as e:
        connection.execute(sa.text("ROLLBACK"))
        print(f"Индекс ix_users_tg_id уже существует или другая ошибка: {e}")

    # Индекс для таблицы master_categories
    try:
        connection.execute(sa.text("COMMIT"))
        op.create_index('ix_master_categories_user_id', 'master_categories', ['user_id'])
    except Exception as e:
        connection.execute(sa.text("ROLLBACK"))
        print(f"Индекс ix_master_categories_user_id уже существует или другая ошибка: {e}")

    # Составной индекс для поиска категорий конкретного мастера
    try:
        connection.execute(sa.text("COMMIT"))
        op.create_index('ix_master_categories_user_category', 'master_categories', ['user_id', 'category'])
    except Exception as e:
        connection.execute(sa.text("ROLLBACK"))
        print(f"Индекс ix_master_categories_user_category уже существует или другая ошибка: {e}")

    # Индекс для поиска мастеров по категории
    try:
        connection.execute(sa.text("COMMIT"))
        op.create_index('ix_master_categories_category', 'master_categories', ['category'])
    except Exception as e:
        connection.execute(sa.text("ROLLBACK"))
        print(f"Индекс ix_master_categories_category уже существует или другая ошибка: {e}")

    # Индекс для таблицы master_specialties
    try:
        connection.execute(sa.text("COMMIT"))
        op.create_index('ix_master_specialties_user_id', 'master_specialties', ['user_id'])
    except Exception as e:
        connection.execute(sa.text("ROLLBACK"))
        print(f"Индекс ix_master_specialties_user_id уже существует или другая ошибка: {e}")

    # Составной индекс для поиска специальностей мастера
    try:
        connection.execute(sa.text("COMMIT"))
        op.create_index('ix_master_specialties_user_specialty', 'master_specialties', ['user_id', 'specialty_id'])
    except Exception as e:
        connection.execute(sa.text("ROLLBACK"))
        print(f"Индекс ix_master_specialties_user_specialty уже существует или другая ошибка: {e}")

    # Индекс для поиска пользователей по специальности
    try:
        connection.execute(sa.text("COMMIT"))
        op.create_index('ix_master_specialties_specialty_id', 'master_specialties', ['specialty_id'])
    except Exception as e:
        connection.execute(sa.text("ROLLBACK"))
        print(f"Индекс ix_master_specialties_specialty_id уже существует или другая ошибка: {e}")


def downgrade():
    """Удаление индексов при откате миграции"""
    
    # Получаем соединение напрямую
    connection = op.get_bind()

    # Удаляем индексы в обратном порядке с обработкой ошибок
    for index_name in [
        'ix_master_specialties_specialty_id',
        'ix_master_specialties_user_specialty',
        'ix_master_specialties_user_id',
        'ix_master_categories_category',
        'ix_master_categories_user_category',
        'ix_master_categories_user_id',
        'ix_users_tg_id',
        'ix_users_phone',
        'ix_users_username',
        'ix_users_role_is_active',
        'ix_users_is_active',
        'ix_users_role'
    ]:
        try:
            connection.execute(sa.text("COMMIT"))
            op.drop_index(index_name)
        except Exception as e:
            connection.execute(sa.text("ROLLBACK"))
            print(f"Ошибка при удалении индекса {index_name}: {e}")