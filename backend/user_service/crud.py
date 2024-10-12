from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_, and_, update
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from datetime import datetime, timedelta 
from backend.user_service import models, schemas
import logging
from firebase_admin import auth
import asyncio
from sqlalchemy.orm import joinedload


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

async def addCustomClaims(uid: str, customClaims: dict):
    try:
        await auth.set_custom_user_claims(uid, customClaims)
        logging.info('Custom claims added successfully')
    except Exception as error:
        logging.error(f'Error adding custom claims: {error}')
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
            if not member:
                raise HTTPException(status_code=404, detail="Member not found")
            trainer_uid, member_uid = trainer.uid, member.uid
        else:
            member = await get_member_by_uid(db, current_user_uid)
            trainer = await get_trainer_by_email(db, other_email)
            if not trainer:
                raise HTTPException(status_code=404, detail="Trainer not found")
            trainer_uid, member_uid = trainer.uid, member.uid
        
        existing_mapping = await db.execute(
            select(models.TrainerMemberMap).where(
                (models.TrainerMemberMap.trainer_uid == trainer_uid) &
                (models.TrainerMemberMap.member_uid == member_uid)
            )
        )
        existing_mapping = existing_mapping.scalar_one_or_none()
        if existing_mapping:
            if existing_mapping.status == models.MappingStatus.accepted:
                raise HTTPException(status_code=400, detail="Mapping already exists and is accepted")
            elif existing_mapping.status == models.MappingStatus.pending:
                raise HTTPException(status_code=409, detail="Mapping already exists and is pending")
        
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
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Unexpected error in create_trainer_member_mapping_request: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

async def get_member_mappings(db: AsyncSession, user_uid: str, is_trainer: bool):
    if is_trainer:
        query = select(
            models.TrainerMemberMap,
            models.Member
        ).join(
            models.Member,
            models.TrainerMemberMap.member_uid == models.Member.uid
        ).where(models.TrainerMemberMap.trainer_uid == user_uid)
    else:
        query = select(
            models.TrainerMemberMap,
            models.Trainer
        ).join(
            models.Trainer,
            models.TrainerMemberMap.trainer_uid == models.Trainer.uid
        ).where(models.TrainerMemberMap.member_uid == user_uid)
    
    result = await db.execute(query)
    mappings = result.fetchall()
    
    mapping_data = []
    for mapping, user in mappings:
        try:
            if is_trainer:
                mapping_info = schemas.MemberMappingInfoWithSessions(
                    mapping_id=mapping.id,
                    uid=user.uid,
                    member_email=user.email,
                    member_first_name=user.first_name,
                    member_last_name=user.last_name,
                    status=mapping.status,
                    remaining_sessions=mapping.remaining_sessions
                )
            else:
                mapping_info = schemas.TrainerMappingInfo(
                    mapping_id=mapping.id,
                    uid=user.uid,
                    trainer_email=user.email,
                    trainer_first_name=user.first_name,
                    trainer_last_name=user.last_name,
                    status=mapping.status,
                    remaining_sessions=mapping.remaining_sessions
                )
            mapping_data.append(mapping_info)
        except Exception as e:
            logging.error(f"Error processing mapping {mapping.id}: {str(e)}")
    
    return mapping_data

async def remove_specific_mapping(db: AsyncSession, current_user_uid: str, other_uid: str, is_trainer: bool):
    try:
        if is_trainer:
            query = select(models.TrainerMemberMap).where(
                (models.TrainerMemberMap.trainer_uid == current_user_uid) &
                (models.TrainerMemberMap.member_uid == other_uid)
            )
        else:
            query = select(models.TrainerMemberMap).where(
                (models.TrainerMemberMap.member_uid == current_user_uid) &
                (models.TrainerMemberMap.trainer_uid == other_uid)
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
        logger.error(f"Database error occurred: {str(e)}")
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error occurred: {str(e)}")
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

async def update_trainer_member_mapping_status(db: AsyncSession, mapping_id: int, new_status: schemas.MappingStatus):
    try:
        stmt = (
            update(models.TrainerMemberMap)
            .where(models.TrainerMemberMap.id == mapping_id)
            .values(status=new_status)
            .returning(models.TrainerMemberMap)
        )
        result = await db.execute(stmt)
        updated_mapping = result.scalar_one_or_none()
        await db.commit()
        return updated_mapping
    except Exception as e:
        await db.rollback()
        logging.error(f"Error in update_trainer_member_mapping_status: {str(e)}")
        raise

async def get_trainer_member_mapping_by_id(db: AsyncSession, mapping_id: int):
    try:
        query = select(models.TrainerMemberMap).where(models.TrainerMemberMap.id == mapping_id)
        result = await db.execute(query)
        mapping = result.scalar_one_or_none()
        return mapping
    except Exception as e:
        logging.error(f"Error in get_trainer_member_mapping_by_id: {str(e)}")
        raise

async def get_trainer_member_mapping(db: AsyncSession, trainer_uid: str, member_uid: str):
    try:
        query = select(models.TrainerMemberMap).where(
            and_(
                models.TrainerMemberMap.trainer_uid == trainer_uid,
                models.TrainerMemberMap.member_uid == member_uid
            )
        )
        result = await db.execute(query)
        mapping = result.scalar_one_or_none()
        return mapping
    except Exception as e:
        logging.error(f"Error in get_trainer_member_mapping: {str(e)}")
        raise

async def get_remaining_sessions(db: AsyncSession, trainer_uid: str, member_uid: str):
    try:
        logging.info(f"Querying remaining sessions for trainer_uid: {trainer_uid}, member_uid: {member_uid}")
        
        query = select(models.TrainerMemberMap).where(
            and_(
                models.TrainerMemberMap.trainer_uid == trainer_uid,
                models.TrainerMemberMap.member_uid == member_uid,
                models.TrainerMemberMap.status == 'accepted'
            )
        )
        result = await db.execute(query)
        mapping = result.scalar_one_or_none()
        
        if mapping:
            logging.info(f"Found mapping with remaining sessions: {mapping.remaining_sessions}")
            return mapping.remaining_sessions
        else:
            logging.warning(f"No accepted mapping found for trainer_uid: {trainer_uid}, member_uid: {member_uid}")
            return None
    except Exception as e:
        logging.error(f"Error in get_remaining_sessions: {str(e)}", exc_info=True)
        raise

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
        logger.error(f"Database error occurred: {str(e)}")
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error occurred: {str(e)}")
        raise

async def schedule_status_update(db: AsyncSession, trainer_uid: str, member_uid: str):
    await asyncio.sleep(2 * 60 * 60)  # Sleep for 2 hours
    await update_trainer_member_mapping_status(db, trainer_uid, member_uid, models.MappingStatus.expired)

async def update_trainer_member_mapping_status(db: AsyncSession, mapping_id: int, new_status: schemas.MappingStatus):
    try:
        stmt = (
            update(models.TrainerMemberMap)
            .where(models.TrainerMemberMap.id == mapping_id)
            .values(status=new_status)
            .returning(models.TrainerMemberMap)
        )
        result = await db.execute(stmt)
        updated_mapping = result.scalar_one_or_none()
        await db.commit()
        return updated_mapping
    except Exception as e:
        await db.rollback()
        logging.error(f"Error in update_trainer_member_mapping_status: {str(e)}")
        raise
        
async def update_member(db: AsyncSession, member: models.Member, member_update: schemas.MemberUpdate):
    update_data = member_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(member, key, value)
    await db.commit()
    await db.refresh(member)
    return member

async def get_trainer_assigned_members(db: AsyncSession, trainer_uid: str):
    try:
        query = select(models.TrainerMemberMap).filter(
            models.TrainerMemberMap.trainer_uid == trainer_uid,
            models.TrainerMemberMap.status == 'accepted'
        ).options(joinedload(models.TrainerMemberMap.member))
        
        result = await db.execute(query)
        mappings = result.unique().scalars().all()
        
        return [schemas.MemberBasicInfo(
            uid=mapping.member.uid,
            email=mapping.member.email,
            first_name=mapping.member.first_name,
            last_name=mapping.member.last_name
        ) for mapping in mappings]
    except Exception as e:
        logger.error(f"Error in get_trainer_assigned_members: {str(e)}")
        raise