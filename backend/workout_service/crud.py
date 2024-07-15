from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.workout_service import models, schemas
import logging

logger = logging.getLogger(__name__)

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.User).filter(models.User.email == email))
    return result.scalar_one_or_none()

async def get_trainer_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.Trainer).filter(models.Trainer.email == email))
    return result.scalar_one_or_none()

async def check_trainer_user_mapping(db: AsyncSession, trainer_id: int, user_id: int):
    result = await db.execute(
        select(models.TrainerUserMap).filter(
            models.TrainerUserMap.trainer_id == trainer_id,
            models.TrainerUserMap.user_id == user_id
        )
    )
    return result.scalar_one_or_none() is not None

async def create_session(db: AsyncSession, session_data: dict):
    try:
        # Ensure session_type_id is in the session_data
        if 'session_type_id' not in session_data:
            raise ValueError("session_type_id is required")

        # Create a new SessionIDMap instance
        new_session = models.SessionIDMap(
            session_type=session_data['session_type_id'],
            workout_date=session_data['workout_date'],
            user_id=session_data['user_id'],
            trainer_id=session_data.get('trainer_id'),  # trainer_id might be optional
            is_pt=session_data['is_pt']
        )

        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        logger.info(f"Session created: {new_session.session_id}")
        return new_session
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        await db.rollback()
        raise