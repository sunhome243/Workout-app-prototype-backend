from sqlalchemy.orm import Session
from . import models, schemas
import bcrypt

# Call user with ID
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.user_id == user_id).first()

# Call trainer with ID
def get_trainer(db: Session, trainer_id: int):
    return db.query(models.Trainer).filter(models.Trainer.trainer_id == trainer_id).first()

# Call user with email
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

# Call trainer with email
def get_trainer_by_email(db: Session, email: str):
    return db.query(models.Trainer).filter(models.Trainer.email == email).first()

# Call multiple users
def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

# Call multiple trainers
def get_trainers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Trainer).offset(skip).limit(limit).all()

# Creating user
def create_user(db: Session, user: schemas.UserCreate):
    salt = bcrypt.gensalt()
    after_hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), salt)

    db_user = models.User(email=user.email, hashed_password=after_hashed_password)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Creating trainer
def create_trainer(db: Session, trainer: schemas.TrainerCreate):
    salt = bcrypt.gensalt()
    after_hashed_password = bcrypt.hashpw(trainer.password.encode('utf-8'), salt)

    db_user = models.Trainer(email=trainer.email, hashed_password=after_hashed_password, first_name=trainer.first_name, last_name=trainer.last_name)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Updating user info
def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate):
    db_user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if db_user:
        #Required field
        db_user.age = user_update.age
        db_user.height = user_update.height
        db_user.weight = user_update.weight
        is_connected=False
        # Optional Update
        if user_update.password:
            salt = bcrypt.gensalt()
            after_hashed_password = bcrypt.hashpw(user_update.password.encode('utf-8'), salt)
            db_user.hashed_password = after_hashed_password
        if user_update.workout_duration:
            db_user.workout_duration = user_update.workout_duration
        if user_update.workout_frequency:
            db_user.workout_frequency = user_update.workout_frequency
        if user_update.workout_goal:
            db_user.workout_goal = user_update.workout_goal

    db.commit()
    db.refresh(db_user)
        
    return db_user
    
# Updating trainer info
def update_trainer(db: Session, trainer_id: int, trainer_update: schemas.TrainerUpdate):
    db_user = db.query(models.Trainer).filter(models.Trainer.trainer_id == trainer_id).first()
    if db_user:
        # Optional Update
        if trainer_update.password:
            salt = bcrypt.gensalt()
            after_hashed_password = bcrypt.hashpw(trainer_update.password.encode('utf-8'), salt)
            db_user.hashed_password = after_hashed_password

    db.commit()
    db.refresh(db_user)
        
    return db_user

def create_trainer_user_mapping(db: Session, mapping: schemas.TrainerUserMapCreate):
    db_trainer = get_trainer(db, mapping.trainer_id)
    db_user = get_user(db, mapping.user_id)
    db_mapping = models.TrainerUserMap(trainer_id=mapping.trainer_id, user_id=mapping.user_id)
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping

