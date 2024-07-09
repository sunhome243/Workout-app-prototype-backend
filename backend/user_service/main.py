import bcrypt
import logging
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Annotated, Union
from . import crud, models, schemas, utils
from .database import get_db
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta

app = FastAPI()  # Create the main FastAPI application

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

router = APIRouter()  # Create an APIRouter

ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Login for both trainer + member
@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user, user_type = await utils.authenticate_member(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = utils.create_access_token(
        data={"sub": user.email, "type": user_type}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user_type": user_type}

# User sign up
@router.post("/users/", response_model=schemas.User)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_user(db=db, user=user)

# Updating a user
@router.patch("/users/me", response_model=schemas.User)
async def update_user(
    current_user: Annotated[models.User, Depends(utils.get_current_member)],
    user_update: schemas.UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        updated_user = await crud.update_user(db, current_user, user_update.model_dump())
        if updated_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Trainer sign up
@router.post("/trainers/", response_model=schemas.Trainer)
async def create_trainer(trainer: schemas.TrainerCreate, db: AsyncSession = Depends(get_db)): 
    return await crud.create_trainer(db=db, trainer=trainer)

# Updating a trainer
@router.patch("/trainers/me", response_model=schemas.Trainer)
async def update_user(
    current_user: Annotated[models.Trainer, Depends(utils.get_current_member)],
    user_update: schemas.TrainerUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        updated_user = await crud.update_trainer(db, current_trainer, trainer_update.model_dump())
        if updated_trainer is None:
            raise HTTPException(status_code=404, detail="User not found")
        return updated_trainer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Only Admin can use. Get all users
@router.get("/users/", response_model=List[schemas.User])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(utils.get_db),
    current_user: schemas.User = Depends(utils.admin_required)
):
    users = await crud.get_users(db, skip=skip, limit=limit)
    return users

# Only Admin can use. Get all trainers
@router.get("/trainers/", response_model=List[schemas.Trainer])
async def read_trainers(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(utils.get_db),
    current_user: schemas.User = Depends(utils.admin_required)
):
    trainers = await crud.get_trainers(db, skip=skip, limit=limit)
    return trainers

# Getting a user with id
@router.get("/users/byid/{user_id}", response_model=schemas.User)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

#Getting a trainer with id
@router.get("/trainers/byid/{trainer_id}", response_model=schemas.Trainer)
async def read_trainer(trainer_id: int, db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_trainer_by_id(db, trainer_id=trainer_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return db_user

# Getting a user with email
@router.get("/users/byemail/{email}", response_model=schemas.User)
async def read_user_email(email: str, db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_user_by_email(db, email=email)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# Getting a trainer with email
@router.get("/trainers/byemail/{email}", response_model=schemas.Trainer)
async def read_trainer_email(email: str, db: AsyncSession = Depends(get_db)):
    db_trainer = await crud.get_trainer_by_email(db, email=email)
    if db_trainer is None:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return db_trainer


@router.post("/trainer-user-mapping/request", response_model=schemas.TrainerUserMappingResponse)
async def request_trainer_user_mapping(
    mapping: schemas.CreateTrainerUserMapping,
    current_user: Union[models.User, models.Trainer] = Depends(utils.get_current_member),
    db: AsyncSession = Depends(utils.get_db)
):
    logging.info(f"Received request to create trainer-user mapping with other_id: {mapping.other_id}")
    logging.info(f"Current user: {current_user}")
    
    is_trainer = isinstance(current_user, models.Trainer)
    logging.info(f"Is trainer: {is_trainer}")
    
    try:
        current_user_id = current_user.trainer_id if is_trainer else current_user.user_id
        
        new_mapping = await crud.create_trainer_user_mapping_request(
            db, 
            current_user_id,
            mapping.other_id,
            is_trainer
        )
        logging.info(f"New mapping request created: {new_mapping}")
        return new_mapping
    except ValueError as e:
        logging.warning(str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error creating mapping request: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create mapping request")

@router.put("/trainer-user-mapping/{mapping_id}/status", response_model=schemas.TrainerUserMappingResponse)
async def update_trainer_user_mapping_status(
    mapping_id: int,
    new_status: schemas.MappingStatus,
    current_user: Union[models.User, models.Trainer] = Depends(utils.get_current_member),
    db: AsyncSession = Depends(utils.get_db)
):
    try:
        current_user_id = current_user.trainer_id if isinstance(current_user, models.Trainer) else current_user.user_id
        updated_mapping = await crud.update_trainer_user_mapping_status(db, mapping_id, current_user_id, new_status)
        return updated_mapping
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error updating mapping status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update mapping status")
    
@router.delete("/trainer-user-mapping/", response_model=schemas.Message)
async def remove_user_mappings(
    current_user: Union[models.User, models.Trainer] = Depends(utils.get_current_member),
    db: AsyncSession = Depends(utils.get_db)
):
    # Check if the current user is a trainer or a regular user
    is_trainer = isinstance(current_user, models.Trainer)
    
    # Determine the correct ID to use
    if is_trainer:
        identifier = current_user.trainer_id
    else:
        identifier = current_user.user_id
    
    # Remove mappings based on the user type
    removed_count = await crud.remove_user_mappings(db, identifier, is_trainer)
    
    if removed_count > 0:
        return {"message": f"Successfully removed {removed_count} trainer-user mapping(s)"}
    else:
        return {"message": "No trainer-user mappings found to remove"}


@router.get("/users/me/", response_model=schemas.User)
async def read_users_me(
    current_user: Annotated[models.User, Depends(utils.get_current_member)],
):
    return current_user

@router.get("/trainers/me/", response_model=schemas.Trainer)
async def read_trainer_me(
    current_trainer: Annotated[models.Trainer, Depends(utils.get_current_member)],
):
    return current_trainer

@router.delete("/users/me/", response_model=schemas.User)
async def delete_users_me(
    current_user: Annotated[models.User, Depends(utils.get_current_member)],
    db: AsyncSession = Depends(utils.get_db)
):
    try:
        # deleting user
        await crud.delete_user(db, current_user)

        return current_user
    except Exception as e:
        await db.rollback()
        logging.error(f"Error deleting user: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete user: {str(e)}")
    
@router.delete("/trainers/me/", response_model=schemas.Trainer)
async def delete_trainers_me(
    current_trainer: Annotated[models.Trainer, Depends(utils.get_current_member)],
    db: AsyncSession = Depends(utils.get_db)
):
    try:
        # deleting user
        await crud.delete_trainer(db, current_trainer)

        return current_trainer
    except Exception as e:
        await db.rollback()
        logging.error(f"Error deleting user: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete trainer: {str(e)}")

app.include_router(router)