"""add_master_categories_table

Revision ID: 903c75f5cd55
Revises: 5e736ec389db
Create Date: 2025-08-30 19:40:51.988430

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '903c75f5cd55'
down_revision: Union[str, None] = '5e736ec389db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создание таблицы master_categories для связи мастеров с категориями заказов
    op.create_table(
        'master_categories',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'category')
    )


def downgrade() -> None:
    # Удаление таблицы master_categories
    op.drop_table('master_categories')
