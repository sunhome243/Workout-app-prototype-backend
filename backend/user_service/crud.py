from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from . import models, schemas
import bcrypt
import logging
from . import utils

async def is_email_unique(db: AsyncSession, email: str) -> bool:
    # Check user table
    user_result = await db.execute(select(models.User).filter(models.User.email == email))
    user = user_result.scalar_one_or_none()
    if user:
        return False

    # Check trainer table
    trainer_result = await db.execute(select(models.Trainer).filter(models.Trainer.email == email))
    trainer = trainer_result.scalar_one_or_none()
    if trainer:
        return False

    return True

# Creating user
async def create_user(db: AsyncSession, user: schemas.UserCreate):
    if not await is_email_unique(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), salt)
    after_hashed_password = hashed_password.decode('utf-8')
    db_user = models.User(email=user.email, hashed_password=after_hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

# Creating trainer
async def create_trainer(db: AsyncSession, trainer: schemas.TrainerCreate):
    if not await is_email_unique(db, trainer.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(trainer.password.encode('utf-8'), salt)
    after_hashed_password = hashed_password.decode('utf-8')
    db_user = models.Trainer(email=trainer.email, hashed_password=after_hashed_password, first_name=trainer.first_name, last_name=trainer.last_name)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

# Call user with ID
async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.User).filter(models.User.user_id == user_id))
    return result.scalar_one_or_none()

# Call trainer with ID
async def get_trainer_by_id(db: AsyncSession, trainer_id: int):
    result = await db.execute(select(models.Trainer).filter(models.Trainer.trainer_id == trainer_id))
    return result.scalar_one_or_none()

# Call user with email
async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.User).filter(models.User.email == email))
    return result.scalar_one_or_none()

# Call trainer with email
async def get_trainer_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.Trainer).filter(models.Trainer.email == email))
    return result.scalar_one_or_none()

# Call multiple users
async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.User).offset(skip).limit(limit))
    return result.scalars().all()

# Call multiple trainers
async def get_trainers(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Trainer).offset(skip).limit(limit))
    return result.scalars().all()

# Updating user info
async def update_user(db: AsyncSession, current_user: models.User, user_update: dict):
    # Prepare update data
    update_data = {k: v for k, v in user_update.items() if v is not None}

    # Handle password change if requested
    if 'new_password' in update_data:
        if 'current_password' not in update_data:
            raise ValueError("Current password is required to change password")
        
        # Verify current password
        if not bcrypt.checkpw(update_data['current_password'].encode('utf-8'), current_user.hashed_password.encode('utf-8')):
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

    # Update the user in the database
    stmt = select(models.User).where(models.User.user_id == current_user.user_id)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()

    if db_user is None:
        return None

    for key, value in update_data.items():
        setattr(db_user, key, value)

    await db.commit()
    await db.refresh(db_user)

    return db_user

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
    stmt = select(models.trainer).where(models.Trainer.trainer_id == current_trainer.trainer_id)
    result = await db.execute(stmt)
    db_trainer = result.scalar_one_or_none()

    if db_trainer is None:
        return None

    for key, value in update_data.items():
        setattr(db_trainer, key, value)

    await db.commit()
    await db.refresh(db_trainer)

    return db_trainer


async def create_trainer_user_mapping_request(db: AsyncSession, current_user_id: int, other_id: int, is_trainer: bool):
    try:
        if is_trainer:
            trainer_id, user_id = current_user_id, other_id
        else:
            trainer_id, user_id = other_id, current_user_id

        logging.debug(f"Attempting to create mapping: trainer_id={trainer_id}, user_id={user_id}")

        # Check if mapping already exists
        existing_mapping = await db.execute(
            select(models.TrainerUserMap).where(
                (models.TrainerUserMap.trainer_id == trainer_id) &
                (models.TrainerUserMap.user_id == user_id)
            )
        )
        if existing_mapping.scalar_one_or_none():
            raise ValueError("This mapping already exists")

        new_status = models.MappingStatus.pending
        logging.debug(f"Creating new mapping with status: {new_status.value}")
        
        db_mapping = models.TrainerUserMap(
            trainer_id=trainer_id, 
            user_id=user_id, 
            status=new_status,
            requester_id=current_user_id  # Add the requester_id
        )
        
        logging.debug(f"New mapping object created: {db_mapping.__dict__}")
        db.add(db_mapping)
        logging.debug("Added mapping to session")
        await db.commit()
        logging.debug("Committed session")
        await db.refresh(db_mapping)
        logging.debug(f"Refreshed mapping object: {db_mapping.__dict__}")
        return db_mapping
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

async def update_trainer_user_mapping_status(db: AsyncSession, mapping_id: int, current_user_id: int, new_status: models.MappingStatus):
    try:
        # Fetch the mapping
        mapping = await db.execute(select(models.TrainerUserMap).where(models.TrainerUserMap.id == mapping_id))
        mapping = mapping.scalar_one_or_none()

        if not mapping:
            raise ValueError("Mapping not found")

        # Check if the current user is the one who didn't request the mapping
        if mapping.requester_id == current_user_id:
            raise ValueError("You cannot update the status of a mapping you requested")

        # Check if the current user is either the trainer or the user in the mapping
        if current_user_id not in (mapping.trainer_id, mapping.user_id):
            raise ValueError("You are not authorized to update this mapping")

        # Update the status
        mapping.status = new_status
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

async def get_user_mappings(db: AsyncSession, user_id: int, is_trainer: bool):
    if is_trainer:
        query = select(models.TrainerUserMap).where(models.TrainerUserMap.trainer_id == user_id)
    else:
        query = select(models.TrainerUserMap).where(models.TrainerUserMap.user_id == user_id)
    
    result = await db.execute(query)
    mappings = result.scalars().all()
    
    mapping_data = []
    for mapping in mappings:
        if is_trainer:
            user = await get_user_by_id(db, mapping.user_id)
            mapping_info = {
                "user_id": user.user_id,
                "user_email": user.email,
                "user_first_name": user.first_name,
                "user_last_name": user.last_name,
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

async def remove_specific_mapping(db: AsyncSession, current_user_id: int, other_id: int, is_trainer: bool) -> bool:
    try:
        if is_trainer:
            query = select(models.TrainerUserMap).where(
                (models.TrainerUserMap.trainer_id == current_user_id) &
                (models.TrainerUserMap.user_id == other_id)
            )
        else:
            query = select(models.TrainerUserMap).where(
                (models.TrainerUserMap.user_id == current_user_id) &
                (models.TrainerUserMap.trainer_id == other_id)
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

async def delete_user(db: AsyncSession, user: models.User):
    await db.execute(delete(models.TrainerUserMap).where(models.TrainerUserMap.user_id == user.user_id))
    await db.delete(user)
    await db.commit()
    
async def delete_trainer(db: AsyncSession, trainer: models.Trainer):
    await db.execute(delete(models.TrainerUserMap).where(models.TrainerUserMap.trainer_id == trainer.trainer_id))
    await db.delete(trainer)
    await db.commit()