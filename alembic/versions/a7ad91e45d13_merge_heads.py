"""merge_heads

Revision ID: a7ad91e45d13
Revises: add_location_updated_at, add_master_id_to_orders, b5efbf33945f
Create Date: 2025-08-29 16:08:08.425257

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7ad91e45d13'
down_revision: Union[str, None] = ('add_location_updated_at', 'add_master_id_to_orders', 'b5efbf33945f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
