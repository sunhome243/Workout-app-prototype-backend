from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_, and_, update
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from datetime import datetime, timedelta 
from . import models, schemas
import logging
from firebase_admin import auth
import asyncio

async def get_member_by_uid(db: AsyncSession, uid: str):
    result = await db.execute(select(models.Member).filter(models.Member.uid == uid))
    return result.scalar_one_or_none()

async def get_trainer_by_uid(db: AsyncSession, uid: str):
    result = await db.execute(select(models.Trainer).filter(models.Trainer.uid == uid))
    return result.scalar_one_or_none()

async def get_member_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.Member).filter(models.Member.email == email))
    return result.scalar_one_or_none()

async def get_trainer_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.Trainer).filter(models.Trainer.email == email))
    return result.scalar_one_or_none()

async def create_member(db: AsyncSession, member: schemas.UserCreate):
    db_member = models.Member(
        uid=member.uid,
        email=member.email,
        first_name=member.first_name,
        last_name=member.last_name,
        role=models.UserRole.member
    )
    db.add(db_member)
    try:
        await db.commit()
        await db.refresh(db_member)
        return db_member
    except Exception as e:
        await db.rollback()
        raise

async def create_trainer(db: AsyncSession, trainer: schemas.UserCreate):
    db_trainer = models.Trainer(
        uid=trainer.uid,
        email=trainer.email,
        first_name=trainer.first_name,
        last_name=trainer.last_name,
        role=models.UserRole.trainer
    )
    db.add(db_trainer)
    try:
        await db.commit()
        await db.refresh(db_trainer)
        return db_trainer
    except Exception as e:
        await db.rollback()
        raise

async def update_member(db: AsyncSession, current_member: models.Member, member_update: dict):
    for key, value in member_update.items():
        setattr(current_member, key, value)
    await db.commit()
    await db.refresh(current_member)
    return current_member

async def update_trainer(db: AsyncSession, current_trainer: models.Trainer, trainer_update: dict):
    for key, value in trainer_update.items():
        setattr(current_trainer, key, value)
    await db.commit()
    await db.refresh(current_trainer)
    return current_trainer

async def create_trainer_member_mapping_request(db: AsyncSession, current_user_uid: str, other_email: str, is_trainer: bool, initial_sessions: int):
    try:
        if is_trainer:
            trainer = await get_trainer_by_uid(db, current_user_uid)
            member = await get_member_by_email(db, other_email)
            trainer_uid, member_uid = trainer.uid, member.uid
        else:
            member = await get_member_by_uid(db, current_user_uid)
            trainer = await get_trainer_by_email(db, other_email)
            trainer_uid, member_uid = trainer.uid, member.uid
        
        existing_mapping = await db.execute(
            select(models.TrainerMemberMap).where(
                (models.TrainerMemberMap.trainer_uid == trainer_uid) &
                (models.TrainerMemberMap.member_uid == member_uid)
            )
        )
        if existing_mapping.scalar_one_or_none():
            raise ValueError("This mapping already exists")
        
        new_status = models.MappingStatus.pending
        db_mapping = models.TrainerMemberMap(
            trainer_uid=trainer_uid,
            member_uid=member_uid,
            status=new_status,
            requester_uid=current_user_uid,
            remaining_sessions=initial_sessions
        )
        db.add(db_mapping)
        await db.commit()
        await db.refresh(db_mapping)
        return db_mapping
    except Exception as e:
        await db.rollback()
        raise

async def update_trainer_member_mapping_status(db: AsyncSession, mapping_id: int, current_user_uid: str, new_status: models.MappingStatus):
    try:
        mapping = await db.execute(select(models.TrainerMemberMap).where(models.TrainerMemberMap.id == mapping_id))
        mapping = mapping.scalar_one_or_none()

        if not mapping:
            raise ValueError("Mapping not found")

        if mapping.requester_uid == current_user_uid:
            raise ValueError("You cannot update the status of a mapping you requested")

        if current_user_uid not in (mapping.trainer_uid, mapping.member_uid):
            raise ValueError("You are not authorized to update this mapping")

        mapping.status = new_status
        
        if new_status == models.MappingStatus.accepted:
            mapping.acceptance_date = datetime.utcnow()

        await db.commit()
        await db.refresh(mapping)
        return mapping
    except SQLAlchemyError as e:
        await db.rollback()
        logging.error(f"Database error occurred: {str(e)}")
        raise
    except ValueError as e:
        logging.warning(str(e))
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Unexpected error occurred: {str(e)}")
        raise

async def get_member_mappings(db: AsyncSession, user_uid: str, is_trainer: bool):
    if is_trainer:
        query = select(models.TrainerMemberMap).where(models.TrainerMemberMap.trainer_uid == user_uid)
    else:
        query = select(models.TrainerMemberMap).where(models.TrainerMemberMap.member_uid == user_uid)
    
    result = await db.execute(query)
    mappings = result.scalars().all()
    
    mapping_data = []
    for mapping in mappings:
        if is_trainer:
            member = await get_member_by_uid(db, mapping.member_uid)
            mapping_info = {
                "uid": member.uid,
                "email": member.email,
                "first_name": member.first_name,
                "last_name": member.last_name,
                "status": mapping.status
            }
        else:
            trainer = await get_trainer_by_uid(db, mapping.trainer_uid)
            mapping_info = {
                "uid": trainer.uid,
                "email": trainer.email,
                "first_name": trainer.first_name,
                "last_name": trainer.last_name,
                "status": mapping.status
            }
        mapping_data.append(mapping_info)
    
    return mapping_data

async def remove_specific_mapping(db: AsyncSession, current_user_uid: str, other_email: str, is_trainer: bool) -> bool:
    try:
        if is_trainer:
            other_user = await get_member_by_email(db, other_email)
            query = select(models.TrainerMemberMap).where(
                (models.TrainerMemberMap.trainer_uid == current_user_uid) &
                (models.TrainerMemberMap.member_uid == other_user.uid)
            )
        else:
            other_user = await get_trainer_by_email(db, other_email)
            query = select(models.TrainerMemberMap).where(
                (models.TrainerMemberMap.member_uid == current_user_uid) &
                (models.TrainerMemberMap.trainer_uid == other_user.uid)
            )
        
        result = await db.execute(query)
        mapping_to_remove = result.scalar_one_or_none()
        
        if mapping_to_remove is None:
            return False

        await db.delete(mapping_to_remove)
        await db.commit()
        return True
    except SQLAlchemyError as e:
        await db.rollback()
        logging.error(f"Database error occurred: {str(e)}")
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Unexpected error occurred: {str(e)}")
        raise

async def delete_member(db: AsyncSession, member: models.Member):
    await db.execute(delete(models.TrainerMemberMap).where(models.TrainerMemberMap.member_uid == member.uid))
    await db.delete(member)
    await db.commit()
    
async def delete_trainer(db: AsyncSession, trainer: models.Trainer):
    await db.execute(delete(models.TrainerMemberMap).where(models.TrainerMemberMap.trainer_uid == trainer.uid))
    await db.delete(trainer)
    await db.commit()

async def get_specific_connected_member_info(db: AsyncSession, trainer_uid: str, member_email: str):
    query = select(models.Member).join(
        models.TrainerMemberMap,
        and_(
            models.TrainerMemberMap.member_uid == models.Member.uid,
            models.TrainerMemberMap.trainer_uid == trainer_uid,
            models.TrainerMemberMap.status == 'accepted',
            models.Member.email == member_email
        )
    )
    
    result = await db.execute(query)
    member = result.scalar_one_or_none()
    
    if member:
        return {
            "uid": member.uid,
            "age": member.age,
            "height": member.height,
            "weight": member.weight,
            "workout_level": member.workout_level,
            "workout_frequency": member.workout_frequency,
            "workout_goal": member.workout_goal,
            "first_name": member.first_name,
            "last_name": member.last_name,
        }
    return None

async def get_trainer_member_mapping(db: AsyncSession, trainer_uid: str, member_uid: str):
    try:
        result = await db.execute(
            select(models.TrainerMemberMap).filter(
                models.TrainerMemberMap.trainer_uid == trainer_uid,
                models.TrainerMemberMap.member_uid == member_uid
            )
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logging.error(f"Error in get_trainer_member_mapping: {str(e)}")
        raise

async def get_remaining_sessions(db: AsyncSession, trainer_uid: str, member_uid: str):
    result = await db.execute(
        select(models.TrainerMemberMap.remaining_sessions)
        .filter(models.TrainerMemberMap.trainer_uid == trainer_uid)
        .filter(models.TrainerMemberMap.member_uid == member_uid)
    )
    return result.scalar_one_or_none()

async def update_sessions(db: AsyncSession, trainer_uid: str, member_uid: str, sessions_to_add: int):
    try:
        stmt = (
            update(models.TrainerMemberMap)
            .where(models.TrainerMemberMap.trainer_uid == trainer_uid)
            .where(models.TrainerMemberMap.member_uid == member_uid)
            .values(remaining_sessions=models.TrainerMemberMap.remaining_sessions + sessions_to_add)
            .returning(models.TrainerMemberMap.remaining_sessions, models.TrainerMemberMap.status)
        )
        result = await db.execute(stmt)
        new_remaining_sessions, current_status = result.first()

        if new_remaining_sessions == 0 and current_status != models.MappingStatus.expired:
            asyncio.create_task(schedule_status_update(db, trainer_uid, member_uid))

        await db.commit()
        return new_remaining_sessions
    except SQLAlchemyError as e:
        await db.rollback()
        logging.error(f"Database error occurred: {str(e)}")
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Unexpected error occurred: {str(e)}")
        raise

async def schedule_status_update(db: AsyncSession, trainer_uid: str, member_uid: str):
    await asyncio.sleep(2 * 60 * 60)  # Sleep for 2 hours
    await update_trainer_member_mapping_status(db, trainer_uid, member_uid, models.MappingStatus.expired)

async def update_trainer_member_mapping_status(db: AsyncSession, trainer_uid: str, member_uid: str, new_status: models.MappingStatus):
    try:
        stmt = (
            update(models.TrainerMemberMap)
            .where(models.TrainerMemberMap.trainer_uid == trainer_uid)
            .where(models.TrainerMemberMap.member_uid == member_uid)
            .values(status=new_status)
        )
        await db.execute(stmt)
        await db.commit()
        logging.info(f"Updated status to {new_status} for trainer {trainer_uid} and member {member_uid}")
    except SQLAlchemyError as e:
        await db.rollback()
        logging.error(f"Database error occurred while updating status: {str(e)}")
        raise
    except Exception as e:
        await db.roll