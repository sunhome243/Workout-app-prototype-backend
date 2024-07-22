"""Set server_default for workout_date

Revision ID: e6d9fe7d129f
Revises: a3a1023bb4fa
Create Date: 2024-07-22 13:53:34.534738

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e6d9fe7d129f'
down_revision: Union[str, None] = 'a3a1023bb4fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:

    pass