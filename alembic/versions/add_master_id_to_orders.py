"""add master_id to orders

Revision ID: add_master_id_to_orders
Revises: 7d5e94623ea9
Create Date: 2023-10-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_master_id_to_orders'
down_revision = '7d5e94623ea9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем колонку master_id в таблицу orders
    op.add_column('orders', sa.Column('master_id', sa.BigInteger(), nullable=True))
    
    # Создаем внешний ключ для master_id, ссылающийся на таблицу users
    op.create_foreign_key(
        'fk_orders_master_id_users',
        'orders', 'users',
        ['master_id'], ['id']
    )


def downgrade() -> None:
    # Удаляем внешний ключ
    op.drop_constraint('fk_orders_master_id_users', 'orders', type_='foreignkey')
    
    # Удаляем колонку master_id
    op.drop_column('orders', 'master_id')
