from sqlalchemy.orm import Session
from . import models, schemas
import bcrypt

# 데이터 읽기 - ID로 사용자 불러오기
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.user_id == user_id).first()

# 데이터 읽기 - Email로 사용자 불러오기
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

# 데이터 읽기 - 여러 사용자 불러오기
def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

# 데이터 생성하기
def create_user(db: Session, user: schemas.UserCreate):
    salt = bcrypt.gensalt()
    after_hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), salt)

    db_user = models.User(email=user.email, hashed_password=after_hashed_password)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate):
    db_user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if db_user:
        #Required field
        db_user.age = user_update.age
        db_user.height = user_update.height
        db_user.weight = user_update.weight
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
    
