"""Add server_default to workout_date

Revision ID: a3a1023bb4fa
Revises: 60cbb0d78c0a
Create Date: 2024-07-22 11:29:34.523448

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision: str = 'a3a1023bb4fa'
down_revision: Union[str, None] = '60cbb0d78c0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:

    pass