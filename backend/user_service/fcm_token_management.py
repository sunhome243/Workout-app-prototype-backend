from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from . import models
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

async def add_fcm_token(db: AsyncSession, user_uid: str, token: str, is_trainer: bool):
    try:
        model = models.Trainer if is_trainer else models.Member
        stmt = (
            update(model)
            .where(model.uid == user_uid)
            .values(fcm_tokens=func.array_append(model.fcm_tokens, token))
            .returning(model.fcm_tokens)
        )
        result = await db.execute(stmt)
        updated_tokens = result.scalar_one()
        await db.commit()
        logger.info(f"FCM token added for user {user_uid}")
        return updated_tokens
    except Exception as e:
        await db.rollback()
        logger.error(f"Error adding FCM token: {str(e)}")
        raise

async def remove_fcm_token(db: AsyncSession, user_uid: str, token: str, is_trainer: bool):
    try:
        model = models.Trainer if is_trainer else models.Member
        stmt = (
            update(model)
            .where(model.uid == user_uid)
            .values(fcm_tokens=func.array_remove(model.fcm_tokens, token))
            .returning(model.fcm_tokens)
        )
        result = await db.execute(stmt)
        updated_tokens = result.scalar_one()
        await db.commit()
        logger.info(f"FCM token removed for user {user_uid}")
        return updated_tokens
    except Exception as e:
        await db.rollback()
        logger.error(f"Error removing FCM token: {str(e)}")
        raise

async def refresh_fcm_token(db: AsyncSession, user_uid: str, old_token: str, new_token: str, is_trainer: bool):
    try:
        model = models.Trainer if is_trainer else models.Member
        stmt = (
            update(model)
            .where(model.uid == user_uid)
            .values(fcm_tokens=func.array_append(func.array_remove(model.fcm_tokens, old_token), new_token))
            .returning(model.fcm_tokens)
        )
        result = await db.execute(stmt)
        updated_tokens = result.scalar_one()
        await db.commit()
        logger.info(f"FCM token refreshed for user {user_uid}")
        return updated_tokens
    except Exception as e:
        await db.rollback()
        logger.error(f"Error refreshing FCM token: {str(e)}")
        raise

async def get_user_fcm_tokens(db: AsyncSession, user_uid: str, is_trainer: bool):
    try:
        model = models.Trainer if is_trainer else models.Member
        stmt = select(model.fcm_tokens).where(model.uid == user_uid)
        result = await db.execute(stmt)
        tokens = result.scalar_one_or_none()
        return tokens or []
    except Exception as e:
        logger.error(f"Error fetching FCM tokens: {str(e)}")
        raise

async def remove_inactive_tokens(db: AsyncSession, days_threshold: int = 60):
    try:
        current_time = datetime.utcnow()
        threshold = current_time - timedelta(days=days_threshold)
        
        for model in [models.Member, models.Trainer]:
            stmt = (
                update(model)
                .where(model.last_active < threshold)
                .values(fcm_tokens=[])
            )
            await db.execute(stmt)
        
        await db.commit()
        logger.info(f"Removed inactive tokens older than {days_threshold} days")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error removing inactive tokens: {str(e)}")
        raise

async def update_user_last_active(db: AsyncSession, user_uid: str, is_trainer: bool):
    try:
        model = models.Trainer if is_trainer else models.Member
        stmt = (
            update(model)
            .where(model.uid == user_uid)
            .values(last_active=datetime.utcnow())
        )
        await db.execute(stmt)
        await db.commit()
        logger.info(f"Updated last active timestamp for user {user_uid}")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating last active timestamp: {str(e)}")
        raise