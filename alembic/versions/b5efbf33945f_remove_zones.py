"""remove_zones

Revision ID: b5efbf33945f
Revises: 8d7a691355fc
Create Date: 2025-08-25 17:45:18.240278

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5efbf33945f'
down_revision: Union[str, None] = '8d7a691355fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Удаляем индекс для зоны в заказах
    op.drop_index('ix_orders_category_zone_status', table_name='orders')
    
    # Создаем новый индекс без зоны
    op.create_index('ix_orders_category_status', 'orders', ['category', 'status'])
    
    # Удаляем колонку zone из таблицы orders
    op.drop_column('orders', 'zone')
    
    # Удаляем колонку zones из таблицы users
    op.drop_column('users', 'zones')


def downgrade() -> None:
    # Добавляем колонку zones в таблицу users
    op.add_column('users', sa.Column('zones', sa.ARRAY(sa.String()), nullable=True))
    
    # Добавляем колонку zone в таблицу orders
    op.add_column('orders', sa.Column('zone', sa.String(), nullable=True))
    
    # Удаляем новый индекс
    op.drop_index('ix_orders_category_status', table_name='orders')
    
    # Создаем старый индекс с зоной
    op.create_index('ix_orders_category_zone_status', 'orders', ['category', 'zone', 'status'])
