from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from . import models, schemas
import bcrypt
import logging

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
async def update_user(db: AsyncSession, user: models.User, user_update: dict):
    if user:
        # Update fields
        for key, value in user_update.items():
            if value is not None:
                if key == 'hashed_password':
                    # Password is already hashed in the update_user endpoint
                    setattr(user, key, value)
                elif hasattr(user, key):
                    setattr(user, key, value)

        await db.commit()
        await db.refresh(user)
        return user
    return None

# Updating trainer info
async def update_trainer(db: AsyncSession, trainer: models.Trainer, trainer_update: dict):
    if trainer:
        # Update fields
        for key, value in trainer_update.items():
            if value is not None:
                if key == 'hashed_password':
                    # Password is already hashed in the update_user endpoint
                    setattr(trainer, key, value)
                elif hasattr(trainer, key):
                    setattr(trainer, key, value)

        await db.commit()
        await db.refresh(trainer)
        return trainer
    return None

async def create_trainer_user_mapping(db: AsyncSession, current_user_id: int, other_id: int, is_trainer: bool):
    try:
        if is_trainer:
            trainer_id, user_id = current_user_id, other_id
        else:
            trainer_id, user_id = other_id, current_user_id

        # Check if mapping already exists
        existing_mapping = await db.execute(
            select(models.TrainerUserMap).where(
                (models.TrainerUserMap.trainer_id == trainer_id) &
                (models.TrainerUserMap.user_id == user_id)
            )
        )
        if existing_mapping.scalar_one_or_none():
            raise ValueError("This mapping already exists")

        db_mapping = models.TrainerUserMap(trainer_id=trainer_id, user_id=user_id)
        db.add(db_mapping)
        await db.commit()
        await db.refresh(db_mapping)
        logging.info(f"Created new trainer-user mapping: trainer_id={trainer_id}, user_id={user_id}")
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
    
async def get_trainer_user_mapping(db: AsyncSession, trainer_id: int, user_id: int):
    query = select(models.TrainerUserMap).options(
        selectinload(models.TrainerUserMap.trainer),
        selectinload(models.TrainerUserMap.user)
    ).filter_by(trainer_id=trainer_id, user_id=user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def remove_user_mappings(db: AsyncSession, identifier: int, is_trainer: bool) -> int:
    try:
        # Select the appropriate column based on user type
        if is_trainer:
            query = select(models.TrainerUserMap).where(models.TrainerUserMap.trainer_id == identifier)
        else:
            query = select(models.TrainerUserMap).where(models.TrainerUserMap.user_id == identifier)
        
        result = await db.execute(query)
        mappings_to_remove = result.scalars().all()
        
        # If no mappings found, return 0
        if not mappings_to_remove:
            return 0

        # Delete the mappings
        for mapping in mappings_to_remove:
            await db.delete(mapping)
        
        await db.commit()
        return len(mappings_to_remove)
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