"""Your migration description

Revision ID: ac4b07712525
Revises: 21ce8187bea2
Create Date: 2024-06-26 09:43:05.741297

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac4b07712525'
down_revision: Union[str, None] = '21ce8187bea2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_user_id', table_name='users')
    op.drop_table('users')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('user_id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('email', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('hashed_password', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('age', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('height', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('weight', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('exercise_duration', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('exercise_frequency', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('exercise_goal', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('exercise_level', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('usertype', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('user_id', name='users_pkey')
    )
    op.create_index('ix_users_user_id', 'users', ['user_id'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    # ### end Alembic commands ###
