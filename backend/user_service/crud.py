from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_, and_, update
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from datetime import datetime, timedelta 
from . import models, schemas
import bcrypt
import logging
from . import utils
import random
import string

async def generate_unique_id(db: AsyncSession, length: int = 5) -> str:
    while True:
        new_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        member_result = await db.execute(select(models.Member).filter(models.Member.member_id == new_id))
        trainer_result = await db.execute(select(models.Trainer).filter(models.Trainer.trainer_id == new_id))
        if not member_result.scalar_one_or_none() and not trainer_result.scalar_one_or_none():
            return new_id

async def is_email_unique(db: AsyncSession, email: str) -> bool:
    # Check member table
    member_result = await db.execute(select(models.Member).filter(models.Member.email == email))
    member = member_result.scalar_one_or_none()
    if member:
        return False

    # Check trainer table
    trainer_result = await db.execute(select(models.Trainer).filter(models.Trainer.email == email))
    trainer = trainer_result.scalar_one_or_none()
    if trainer:
        return False

    return True

# Creating member
async def create_member(db: AsyncSession, member: schemas.MemberCreate):
    if not await is_email_unique(db, member.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(member.password.encode('utf-8'), salt)
    after_hashed_password = hashed_password.decode('utf-8')
    unique_id = await generate_unique_id(db)
    db_member = models.Member(member_id=unique_id,email=member.email, hashed_password=after_hashed_password, first_name=member.first_name, last_name=member.last_name, role=models.UserRole.member.value)
    db.add(db_member)
    await db.commit()
    await db.refresh(db_member)
    return db_member

# Creating trainer
async def create_trainer(db: AsyncSession, trainer: schemas.TrainerCreate):
    if not await is_email_unique(db, trainer.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(trainer.password.encode('utf-8'), salt)
    after_hashed_password = hashed_password.decode('utf-8')
    unique_id = await generate_unique_id(db)
    db_member = models.Trainer(trainer_id=unique_id, email=trainer.email, hashed_password=after_hashed_password, first_name=trainer.first_name, last_name=trainer.last_name)
    db.add(db_member)
    await db.commit()
    await db.refresh(db_member)
    return db_member

# Call member with ID
async def get_member_by_id(db: AsyncSession, member_id: str):
    result = await db.execute(select(models.Member).filter(models.Member.member_id == member_id))
    return result.scalar_one_or_none()

# Call trainer with ID
async def get_trainer_by_id(db: AsyncSession, trainer_id: str):
    result = await db.execute(select(models.Trainer).filter(models.Trainer.trainer_id == trainer_id))
    return result.scalar_one_or_none()

# Call member with email
async def get_member_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.Member).filter(models.Member.email == email))
    return result.scalar_one_or_none()

# Call trainer with email
async def get_trainer_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.Trainer).filter(models.Trainer.email == email))
    return result.scalar_one_or_none()

# Call multiple members
async def get_members(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Member).offset(skip).limit(limit))
    return result.scalars().all()

# Call multiple trainers
async def get_trainers(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Trainer).offset(skip).limit(limit))
    return result.scalars().all()

# Updating member info
async def update_member(db: AsyncSession, current_member: models.Member, member_update: dict):
    # Prepare update data
    update_data = {k: v for k, v in member_update.items() if v is not None}

    # Handle password change if requested
    if 'new_password' in update_data:
        if 'current_password' not in update_data:
            raise ValueError("Current password is required to change password")
        
        # Verify current password
        if not bcrypt.checkpw(update_data['current_password'].encode('utf-8'), current_member.hashed_password.encode('utf-8')):
            raise ValueError("Incorrect current password")

        # Validate new password
        utils.validate_password(update_data['new_password'])

        # Hash the new password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(update_data['new_password'].encode('utf-8'), salt)
        update_data['hashed_password'] = hashed_password.decode('utf-8')

        # Remove password fields from update_data
        del update_data['new_password']
        del update_data['current_password']

    # Update the member in the database
    stmt = select(models.Member).where(models.Member.member_id == current_member.member_id)
    result = await db.execute(stmt)
    db_member = result.scalar_one_or_none()

    if db_member is None:
        return None

    for key, value in update_data.items():
        setattr(db_member, key, value)

    await db.commit()
    await db.refresh(db_member)

    return db_member

# Updating trainer info
async def update_trainer(db: AsyncSession, current_trainer: models.Trainer, trainer_update: dict):
    # Prepare update data
    update_data = {k: v for k, v in trainer_update.items() if v is not None}

    # Handle password change if reqFuuested
    if 'new_password' in update_data:
        if 'current_password' not in update_data:
            raise ValueError("Current password is required to change password")
        
        # Verify current password
        if not bcrypt.checkpw(update_data['current_password'].encode('utf-8'), current_trainer.hashed_password.encode('utf-8')):
            raise ValueError("Incorrect current password")

        # Validate new password
        utils.validate_password(update_data['new_password'])

        # Hash the new password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(update_data['new_password'].encode('utf-8'), salt)
        update_data['hashed_password'] = hashed_password.decode('utf-8')

        # Remove password fields from update_data
        del update_data['new_password']
        del update_data['current_password']

    # Update the trainer in the database
    stmt = select(models.Trainer).where(models.Trainer.trainer_id == current_trainer.trainer_id)
    result = await db.execute(stmt)
    db_trainer = result.scalar_one_or_none()

    if db_trainer is None:
        return None

    for key, value in update_data.items():
        setattr(db_trainer, key, value)

    await db.commit()
    await db.refresh(db_trainer)

    return db_trainer


async def create_trainer_member_mapping_request(db: AsyncSession, current_member_id: str, other_id: str, is_trainer: bool, initial_sessions: int):
    try:
        if is_trainer:
            trainer_id, member_id = current_member_id, other_id
        else:
            trainer_id, member_id = other_id, current_member_id
        
        # Check if mapping already exists
        existing_mapping = await db.execute(
            select(models.TrainerMemberMap).where(
                (models.TrainerMemberMap.trainer_id == trainer_id) &
                (models.TrainerMemberMap.member_id == member_id)
            )
        )
        if existing_mapping.scalar_one_or_none():
            raise ValueError("This mapping already exists")
        
        new_status = models.MappingStatus.pending
        db_mapping = models.TrainerMemberMap(
            trainer_id=trainer_id,
            member_id=member_id,
            status=new_status,
            requester_id=current_member_id,
            remaining_sessions=initial_sessions
        )
        db.add(db_mapping)
        await db.commit()
        await db.refresh(db_mapping)
        return db_mapping
    except Exception as e:
        await db.rollback()
        raise

async def update_trainer_member_mapping_status(db: AsyncSession, mapping_id: int, current_member_id: str, new_status: models.MappingStatus):
    try:
        # Fetch the mapping
        mapping = await db.execute(select(models.TrainerMemberMap).where(models.TrainerMemberMap.id == mapping_id))
        mapping = mapping.scalar_one_or_none()

        if not mapping:
            raise ValueError("Mapping not found")

        # Check if the current member is the one who didn't request the mapping
        if mapping.requester_id == current_member_id:
            raise ValueError("You cannot update the status of a mapping you requested")

        # Check if the current member is either the trainer or the member in the mapping
        if current_member_id not in (mapping.trainer_id, mapping.member_id):
            raise ValueError("You are not authorized to update this mapping")

        # Update the status
        mapping.status = new_status
        
        # If the new status is 'accepted', set the acceptance_date
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

async def get_member_mappings(db: AsyncSession, member_id: str, is_trainer: bool):
    if is_trainer:
        query = select(models.TrainerMemberMap).where(models.TrainerMemberMap.trainer_id == member_id)
    else:
        query = select(models.TrainerMemberMap).where(models.TrainerMemberMap.member_id == member_id)
    
    result = await db.execute(query)
    mappings = result.scalars().all()
    
    mapping_data = []
    for mapping in mappings:
        if is_trainer:
            member = await get_member_by_id(db, mapping.member_id)
            mapping_info = {
                "member_id": member.member_id,
                "member_email": member.email,
                "member_first_name": member.first_name,
                "member_last_name": member.last_name,
                "status": mapping.status
            }
        else:
            trainer = await get_trainer_by_id(db, mapping.trainer_id)
            mapping_info = {
                "trainer_id": trainer.trainer_id,
                "trainer_email": trainer.email,
                "trainer_first_name": trainer.first_name,
                "trainer_last_name": trainer.last_name,
                "status": mapping.status
            }
        mapping_data.append(mapping_info)
    
    return mapping_data

async def remove_specific_mapping(db: AsyncSession, current_member_id: str, other_id: str, is_trainer: bool) -> bool:
    try:
        if is_trainer:
            query = select(models.TrainerMemberMap).where(
                (models.TrainerMemberMap.trainer_id == current_member_id) &
                (models.TrainerMemberMap.member_id == other_id)
            )
        else:
            query = select(models.TrainerMemberMap).where(
                (models.TrainerMemberMap.member_id == current_member_id) &
                (models.TrainerMemberMap.trainer_id == other_id)
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
    await db.execute(delete(models.TrainerMemberMap).where(models.TrainerMemberMap.member_id == member.member_id))
    await db.delete(member)
    await db.commit()
    
async def delete_trainer(db: AsyncSession, trainer: models.Trainer):
    await db.execute(delete(models.TrainerMemberMap).where(models.TrainerMemberMap.trainer_id == trainer.trainer_id))
    await db.delete(trainer)
    await db.commit()

async def get_specific_connected_member_info(db: AsyncSession, trainer_id: str, member_id: str):
    query = select(models.Member).join(
        models.TrainerMemberMap,
        and_(
            models.TrainerMemberMap.member_id == models.Member.member_id,
            models.TrainerMemberMap.trainer_id == trainer_id,
            models.TrainerMemberMap.status == 'accepted',
            models.Member.member_id == member_id
        )
    )
    
    result = await db.execute(query)
    member = result.scalar_one_or_none()
    
    if member:
        return {
            "member_id": member.member_id,
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

async def get_trainer_member_mapping(db: AsyncSession, trainer_id: str, member_id: str):
    try:
        result = await db.execute(
            select(models.TrainerMemberMap).filter(
                models.TrainerMemberMap.trainer_id == trainer_id,
                models.TrainerMemberMap.member_id == member_id
            )
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logging.error(f"Error in get_trainer_member_mapping: {str(e)}")
        raise

async def get_remaining_sessions(db: AsyncSession, trainer_id: str, member_id: str):
    result = await db.execute(
        select(models.TrainerMemberMap.remaining_sessions)
        .filter(models.TrainerMemberMap.trainer_id == trainer_id)
        .filter(models.TrainerMemberMap.member_id == member_id)
    )
    return result.scalar_one_or_none()

async def update_sessions(db: AsyncSession, trainer_id: str, member_id: str, sessions_to_add: int):
    stmt = (
        update(models.TrainerMemberMap)
        .where(models.TrainerMemberMap.trainer_id == trainer_id)
        .where(models.TrainerMemberMap.member_id == member_id)
        .values(remaining_sessions=models.TrainerMemberMap.remaining_sessions + sessions_to_add)
    )
    await db.execute(stmt)
    await db.commit()
    return await get_remaining_sessions(db, trainer_id, member_id)