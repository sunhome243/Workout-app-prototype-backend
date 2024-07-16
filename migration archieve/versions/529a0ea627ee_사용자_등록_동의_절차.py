"""사용자 등록 동의 절차

Revision ID: 529a0ea627ee
Revises: 1ce030748706
Create Date: 2024-07-09 10:27:09.095852

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '529a0ea627ee'
down_revision: Union[str, None] = '1ce030748706'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
    
def upgrade():
    # Create the enum type
    op.execute("CREATE TYPE mappingstatus AS ENUM ('pending', 'accepted')")
    
    # Add the status column to the existing table
    op.add_column('trainer_user_mapping', sa.Column('status', postgresql.ENUM('pending', 'accepted', name='mappingstatus'), nullable=True))
    op.add_column('trainer_user_mapping', sa.Column('id', sa.Integer(), nullable=False))
    op.create_index(op.f('ix_trainer_user_mapping_id'), 'trainer_user_mapping', ['id'], unique=False)
    
    # Set the default value for existing rows
    op.execute("UPDATE trainer_user_mapping SET status = 'accepted'")
    
    # Make the status column non-nullable after setting default values
    op.alter_column('trainer_user_mapping', 'status', nullable=False)

def downgrade():
    # Remove the status column
    op.drop_column('trainer_user_mapping', 'status')
    
    # Drop the enum type
    op.execute("DROP TYPE mappingstatus")
