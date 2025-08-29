"""Add is_active field to User model

Revision ID: add_is_active_field
Revises: add_admin_fields
Create Date: 2025-08-15 23:38:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_is_active_field'
down_revision = 'add_admin_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Пустая миграция, так как колонка is_active уже добавляется в add_admin_fields.py
    pass


def downgrade():
    # Удаляем поле is_active
    op.drop_column('users', 'is_active')