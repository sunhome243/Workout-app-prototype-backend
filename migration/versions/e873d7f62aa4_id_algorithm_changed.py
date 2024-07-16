"""id algorithm changed

Revision ID: e873d7f62aa4
Revises: 0be209f20ea5
Create Date: 2024-07-15 14:55:16.611516

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e873d7f62aa4'
down_revision: Union[str, None] = '0be209f20ea5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Remove foreign key constraints
    op.drop_constraint('trainer_user_mapping_trainer_id_fkey', 'trainer_user_mapping', type_='foreignkey')
    op.drop_constraint('trainer_user_mapping_user_id_fkey', 'trainer_user_mapping', type_='foreignkey')

    # Alter column types in trainers table
    op.execute("ALTER TABLE trainers ALTER COLUMN trainer_id TYPE VARCHAR USING trainer_id::VARCHAR")

    # Alter column types in users table
    op.execute("ALTER TABLE users ALTER COLUMN user_id TYPE VARCHAR USING user_id::VARCHAR")

    # Alter column types in trainer_user_mapping table
    op.execute("ALTER TABLE trainer_user_mapping ALTER COLUMN trainer_id TYPE VARCHAR USING trainer_id::VARCHAR")
    op.execute("ALTER TABLE trainer_user_mapping ALTER COLUMN user_id TYPE VARCHAR USING user_id::VARCHAR")
    op.execute("ALTER TABLE trainer_user_mapping ALTER COLUMN requester_id TYPE VARCHAR USING requester_id::VARCHAR")

    # Re-add foreign key constraints
    op.create_foreign_key('trainer_user_mapping_trainer_id_fkey', 'trainer_user_mapping', 'trainers', ['trainer_id'], ['trainer_id'])
    op.create_foreign_key('trainer_user_mapping_user_id_fkey', 'trainer_user_mapping', 'users', ['user_id'], ['user_id'])

def downgrade():
    # Remove foreign key constraints
    op.drop_constraint('trainer_user_mapping_trainer_id_fkey', 'trainer_user_mapping', type_='foreignkey')
    op.drop_constraint('trainer_user_mapping_user_id_fkey', 'trainer_user_mapping', type_='foreignkey')

    # Alter column types back to INTEGER
    op.execute("ALTER TABLE trainers ALTER COLUMN trainer_id TYPE INTEGER USING trainer_id::INTEGER")
    op.execute("ALTER TABLE users ALTER COLUMN user_id TYPE INTEGER USING user_id::INTEGER")
    op.execute("ALTER TABLE trainer_user_mapping ALTER COLUMN trainer_id TYPE INTEGER USING trainer_id::INTEGER")
    op.execute("ALTER TABLE trainer_user_mapping ALTER COLUMN user_id TYPE INTEGER USING user_id::INTEGER")
    op.execute("ALTER TABLE trainer_user_mapping ALTER COLUMN requester_id TYPE INTEGER USING requester_id::INTEGER")

    # Re-add foreign key constraints
    op.create_foreign_key('trainer_user_mapping_trainer_id_fkey', 'trainer_user_mapping', 'trainers', ['trainer_id'], ['trainer_id'])
    op.create_foreign_key('trainer_user_mapping_user_id_fkey', 'trainer_user_mapping', 'users', ['user_id'], ['user_id'])