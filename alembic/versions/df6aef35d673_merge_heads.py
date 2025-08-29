"""merge heads

Revision ID: df6aef35d673
Revises: add_is_active_field, f55f6c66afcf
Create Date: 2025-08-24 15:05:21.274284

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df6aef35d673'
down_revision: Union[str, None] = ('add_is_active_field', 'f55f6c66afcf')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
