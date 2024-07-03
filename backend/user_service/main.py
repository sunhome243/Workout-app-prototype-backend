from typing import List, Annotated
import uvicorn

from fastapi import Depends, FastAPI, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from . import crud, models, schemas, utils
from .database import SessionLocal, engine, get_db
import os


models.Base.metadata.create_all(bind=engine)
app = FastAPI()
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# User sign up
@app.post("/users/", response_model=schemas.User)
def create_member(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email (db, email = user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

# Trainer sign up
@app.post("/trainers/", response_model=schemas.Trainer)
def create_member(trainer: schemas.TrainerCreate, db: Session = Depends(get_db)):
    db_user = crud.get_trainer_by_email (db, email = trainer.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_trainer(db=db, trainer=trainer)

@app.get("/users/", response_model=List[schemas.User])
def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(utils.get_db),
    current_user: schemas.User = Depends(utils.admin_required)
):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@app.get("/trainers/", response_model=List[schemas.Trainer])
def read_trainers(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(utils.get_db),
    current_user: schemas.User = Depends(utils.admin_required)
):
    trainers = crud.get_trainers(db, skip=skip, limit=limit)
    return trainers

# Getting a user with id !NEED CREDENTIAL!
@app.get("/users/byid/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

#Getting a trainer with id !NEED CREDENTIAL!
@app.get("/trainers/byid/{trainer_id}", response_model=schemas.Trainer)
def read_trainer(trainer_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_trainer(db, trainer_id=trainer_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return db_user

# Getting a user with email
@app.get("/users/byemail/{email}", response_model=schemas.User)
def read_user_email(email: str, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=email)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# Getting a trainer with email
@app.get("/trainers/byemail/{email}", response_model=schemas.Trainer)
def read_trainer_email(email: str, db: Session = Depends(get_db)):
    db_trainer = crud.get_trainer_by_email(db, email=email)
    if db_trainer is None:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return db_trainer

# Updating a user with id !NEED CREDENTIAL!
@app.put("/users/{user_id}", response_model = schemas.User)
def update_user(user_id: int, user_update: schemas.UserUpdate, db: Session = Depends(get_db)):
    db_user = crud.update_user(db, user_id=user_id, user_update=user_update)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# Updating a trainer with id !NEED CREDENTIAL!
@app.put("/trainers/{trainer_id}", response_model = schemas.Trainer)
def update_trainer(trainer_id: int, trainer_update: schemas.TrainerUpdate, db: Session = Depends(get_db)):
    db_user = crud.update_trainer(db, trainer_id=trainer_id, trainer_update=trainer_update)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return db_user

@app.post("/trainer-user-mapping/", response_model=schemas.TrainerUserMap)
def create_trainer_user_mapping(mapping: schemas.TrainerUserMapCreate, db: Session = Depends(get_db)):
    # Check if user_id exists
    user = crud.get_user(db, mapping.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User do not exist")
    
    # Check if trainer_id exists
    trainer = crud.get_trainer(db, mapping.trainer_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer do not exist")

    return crud.create_trainer_user_mapping(db=db, mapping=mapping)

# @app.delete("/users/me", response_model=schemas.User)
# def delete_user_me(token: Annotated[str, Depends(oauth2_scheme)], current_user: schemas.User = Depends(utils.get_current_user), db: Session = Depends(SessionLocal)):
#     try:
#         crud.delete_user(db, current_user)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")
#     return current_user

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(utils.get_db)]
) -> schemas.Token:
    user = utils.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = utils.create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    return schemas.Token(access_token=access_token, token_type="bearer")

@app.get("/users/me/", response_model=schemas.User)
async def read_users_me(
    current_user: Annotated[models.User, Depends(utils.get_current_active_user)],
):
    return current_user


@app.get("/users/me/items/")
async def read_own_items(
    current_user: Annotated[models.User, Depends(utils.get_current_active_user)],
):
    return [{"item_id": "Foo", "owner": current_user.email}]