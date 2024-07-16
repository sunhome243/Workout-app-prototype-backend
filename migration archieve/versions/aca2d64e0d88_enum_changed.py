"""enum changed

Revision ID: aca2d64e0d88
Revises: e873d7f62aa4
Create Date: 2024-07-15 16:13:17.737234

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'aca2d64e0d88'
down_revision: Union[str, None] = 'e873d7f62aa4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Create Enum types
    userrole = postgresql.ENUM('user', 'trainer', name='userrole', create_type=False)
    userrole.create(op.get_bind())

    mappingstatus = postgresql.ENUM('pending', 'accepted', name='mappingstatus', create_type=False)
    mappingstatus.create(op.get_bind())

    # Update columns to use new Enum types
    op.alter_column('users', 'role',
                    existing_type=sa.VARCHAR(),
                    type_=sa.Enum('user', 'trainer', name='userrole'),
                    postgresql_using="role::userrole")

    op.alter_column('trainers', 'role',
                    existing_type=sa.VARCHAR(),
                    type_=sa.Enum('user', 'trainer', name='userrole'),
                    postgresql_using="role::userrole")

    op.alter_column('trainer_user_mapping', 'status',
                    existing_type=sa.VARCHAR(),
                    type_=sa.Enum('pending', 'accepted', name='mappingstatus'),
                    postgresql_using="status::mappingstatus")

def downgrade():
    # Revert columns to VARCHAR
    op.alter_column('users', 'role', type_=sa.VARCHAR(), nullable=True)
    op.alter_column('trainers', 'role', type_=sa.VARCHAR(), nullable=True)
    op.alter_column('trainer_user_mapping', 'status', type_=sa.VARCHAR(), nullable=True)

    # Drop Enum types
    op.execute("DROP TYPE userrole")
    op.execute("DROP TYPE mappingstatus")