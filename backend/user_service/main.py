import bcrypt
import logging
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Annotated
from . import crud, models, schemas, utils
from .database import get_db
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

app = FastAPI()  # Create the main FastAPI application
router = APIRouter()  # Create an APIRouter

ACCESS_TOKEN_EXPIRE_MINUTES = 30

# User sign up
@router.post("/users/", response_model=schemas.User)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    await crud.get_user_by_email(db, email=user.email)
    return await crud.create_user(db=db, user=user)

# Trainer sign up
@router.post("/trainers/", response_model=schemas.Trainer)
async def create_trainer(trainer: schemas.TrainerCreate, db: AsyncSession = Depends(get_db)): 
    await crud.get_trainer_by_email (db, email = trainer.email)
    return await crud.create_trainer(db=db, trainer=trainer)

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

# Updating a user
@router.put("/users/me", response_model=schemas.User)
async def update_user(
    current_user: Annotated[models.User, Depends(utils.get_current_member)],
    user_update: schemas.UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    salt = bcrypt.gensalt()
    # Verify current password using authenticate_member
    authenticated_user = await utils.authenticate_member(db, current_user.email, user_update.current_password)
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )

    # Prepare update data
    update_data = user_update.model_dump(exclude={'current_password', 'new_password', 'confirm_password'})

    # Update password if new password is provided
    if user_update.new_password:
        hashed_password = bcrypt.hashpw(user_update.new_password.encode('utf-8'), salt)
        after_hashed_password = hashed_password.decode('utf-8')
        update_data['hashed_password'] = after_hashed_password

    # Remove None values from update_data
    update_data = {k: v for k, v in update_data.items() if v is not None}

    # Update the user in the database
    updated_user = await crud.update_user(db, user=current_user, user_update=update_data)
    if updated_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

# Updating a trainer
@router.put("/trainers/", response_model = schemas.Trainer)
async def update_trainer(
    current_trainer: Annotated[models.Trainer, Depends(utils.get_current_member)],
    trainer_update: schemas.TrainerUpdate,
    db: AsyncSession = Depends(get_db)
):
    salt = bcrypt.gensalt()
    # Verify current password using authenticate_member
    authenticated_trainer = await utils.authenticate_member(db, current_trainer.email, trainer_update.current_password)
    if not authenticated_trainer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )

    # Prepare update data
    update_data = trainer_update.model_dump(exclude={'current_password', 'new_password', 'confirm_password'})

    # Update password if new password is provided
    if trainer_update.new_password:
        hashed_password = bcrypt.hashpw(trainer_update.new_password.encode('utf-8'), salt)
        after_hashed_password = hashed_password.decode('utf-8')
        update_data['hashed_password'] = after_hashed_password

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
    db_user = await crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

#Getting a trainer with id
@router.get("/trainers/byid/{trainer_id}", response_model=schemas.Trainer)
async def read_trainer(trainer_id: int, db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_trainer(db, trainer_id=trainer_id)
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
    return await db_trainer


@router.post("/trainer-user-mapping/", response_model=schemas.TrainerUserMap)
def create_trainer_user_mapping(mapping: schemas.TrainerUserMapCreate, db: AsyncSession = Depends(get_db)):
    # Check if user_id exists
    user = crud.get_user(db, mapping.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User do not exist")
    
    # Check if trainer_id exists
    trainer = crud.get_trainer(db, mapping.trainer_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer do not exist")

    return crud.create_trainer_user_mapping(db=db, mapping=mapping)

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
        await db.commit()

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
        await db.commit()

        return current_trainer
    except Exception as e:
        await db.rollback()
        logging.error(f"Error deleting user: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete trainer: {str(e)}")

app.include_router(router)