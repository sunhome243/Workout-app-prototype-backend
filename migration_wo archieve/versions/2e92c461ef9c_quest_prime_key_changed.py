"""quest prime key changed
Revision ID: 2e92c461ef9c
Revises: 16d4a79ae96e
Create Date: 2024-07-16 11:10:25.180697
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2e92c461ef9c'
down_revision: Union[str, None] = '16d4a79ae96e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add new columns to quest_workout_sets, allowing NULL initially
    op.add_column('quest_workout_sets', sa.Column('quest_id', sa.Integer(), nullable=True))
    op.add_column('quest_workout_sets', sa.Column('workout_key', sa.Integer(), nullable=True))

    # Use raw SQL to update the new columns based on the existing data
    op.execute("""
    UPDATE quest_workout_sets
    SET quest_id = quest_workouts.quest_id,
        workout_key = quest_workouts.workout_key
    FROM quest_workouts
    WHERE quest_workout_sets.workout_id = quest_workouts.id
    """)

    # Now alter the columns to not allow NULL
    op.alter_column('quest_workout_sets', 'quest_id', nullable=False)
    op.alter_column('quest_workout_sets', 'workout_key', nullable=False)

    # Create unique constraint on quest_workouts
    op.create_unique_constraint('uq_quest_workout', 'quest_workouts', ['quest_id', 'workout_key'])

    # Drop existing foreign key constraint
    op.drop_constraint('quest_workout_sets_workout_id_fkey', 'quest_workout_sets', type_='foreignkey')

    # Create new foreign key constraint
    op.create_foreign_key(
        'fk_quest_workout_set_workout', 'quest_workout_sets', 'quest_workouts',
        ['quest_id', 'workout_key'], ['quest_id', 'workout_key']
    )

    # Drop old columns
    op.drop_column('quest_workout_sets', 'workout_id')
    op.drop_column('quest_workout_sets', 'id')
    op.drop_column('quest_workouts', 'id')

def downgrade() -> None:
    # Add back old columns
    op.add_column('quest_workouts', sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False))
    op.add_column('quest_workout_sets', sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False))
    op.add_column('quest_workout_sets', sa.Column('workout_id', sa.INTEGER(), autoincrement=False, nullable=True))

    # Update workout_id based on quest_id and workout_key
    op.execute("""
    UPDATE quest_workout_sets
    SET workout_id = quest_workouts.id
    FROM quest_workouts
    WHERE quest_workout_sets.quest_id = quest_workouts.quest_id
    AND quest_workout_sets.workout_key = quest_workouts.workout_key
    """)

    # Make workout_id not nullable
    op.alter_column('quest_workout_sets', 'workout_id', nullable=False)

    # Drop new foreign key constraint
    op.drop_constraint('fk_quest_workout_set_workout', 'quest_workout_sets', type_='foreignkey')

    # Drop unique constraint
    op.drop_constraint('uq_quest_workout', 'quest_workouts', type_='unique')

    # Recreate old foreign key constraint
    op.create_foreign_key('quest_workout_sets_workout_id_fkey', 'quest_workout_sets', 'quest_workouts', ['workout_id'], ['id'])

    # Drop new columns
    op.drop_column('quest_workout_sets', 'workout_key')
    op.drop_column('quest_workout_sets', 'quest_id')