from typing import List
import uvicorn

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import SessionLocal, engine, get_db

models.Base.metadata.create_all(bind=engine)
app = FastAPI()

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

# Calling all users !NEED CREDENTIAL!
@app.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

# Calling all trainers !NEED CREDENTIAL!
@app.get("/trainers/", response_model=List[schemas.Trainer])
def read_trainers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
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

