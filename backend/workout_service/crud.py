from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas
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
        new_session = models.SessionIDMap(**session_data)
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        logger.info(f"Session created: {new_session.session_id}")
        return new_session
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        await db.rollback()
        raise