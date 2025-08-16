"""Add admin fields to User model

Revision ID: add_admin_fields
Revises: dc5962138348
Create Date: 2025-08-15 23:35:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_admin_fields'
down_revision = 'dc5962138348'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем поля username, hashed_password, email и is_active для администраторов
    op.add_column('users', sa.Column('username', sa.String(), nullable=True))
    op.add_column('users', sa.Column('hashed_password', sa.String(), nullable=True))
    op.add_column('users', sa.Column('email', sa.String(), nullable=True))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'))
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)


def downgrade():
    # Удаляем добавленные поля
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_column('users', 'email')
    op.drop_column('users', 'hashed_password')
    op.drop_column('users', 'username')
    # Проверяем существование колонки is_active перед удалением
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = inspector.get_columns('users')
    if any(col['name'] == 'is_active' for col in columns):
        op.drop_column('users', 'is_active')