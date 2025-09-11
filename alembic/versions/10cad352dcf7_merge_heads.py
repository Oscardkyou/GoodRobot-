"""merge_heads

Revision ID: 10cad352dcf7
Revises: 903c75f5cd55, add_performance_indexes
Create Date: 2025-09-05 21:24:22.130071

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10cad352dcf7'
down_revision: Union[str, None] = ('903c75f5cd55', 'add_performance_indexes')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
