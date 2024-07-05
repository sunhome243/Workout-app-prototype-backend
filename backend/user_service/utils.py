from datetime import datetime, timedelta
from typing import Optional, Annotated
from sqlalchemy import select
import jwt
from jwt.exceptions import PyJWTError 
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import pytz
from . import schemas, models
from .database import AsyncSession, get_db
from . import crud  

SECRET_KEY = "LcdBKEBUqF3F12SFU0JhP0061PXJGQUp"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 20
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_type: str = payload.get("type")
        if email is None or user_type is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception
    if user_type == 'user':
        user = await crud.get_user_by_email(db, email)
    elif user_type == 'trainer':
        user = await crud.get_trainer_by_email(db, email)
    else:
        raise credentials_exception
    if user is None:
        raise credentials_exception
    return user

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

async def authenticate_user(db: AsyncSession, email: str, password: str):
    # Check user table
    user_result = await db.execute(select(models.User).filter(models.User.email == email))
    user = user_result.scalar_one_or_none()
    if user and verify_password(password, user.hashed_password):
        return user, 'user'
    # Check trainer table
    trainer_result = await db.execute(select(models.Trainer).filter(models.Trainer.email == email))
    trainer = trainer_result.scalar_one_or_none()
    if trainer and verify_password(password, trainer.hashed_password):
        return trainer, 'trainer'
    return None, None

async def admin_required(current_user: schemas.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user