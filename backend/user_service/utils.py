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
import os
import logging
import re
import datetime as dt  # Renamed datetime to dt to avoid conflict with datetime module

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = dt.datetime.now(dt.timezone.utc) + expires_delta
    else:
        expire = dt.datetime.now(dt.timezone.utc) + timedelta(minutes=15)
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
        id: str = payload.get("sub")
        member_type: str = payload.get("type")
        if id is None or member_type is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if member_type == 'member':
        member = await crud.get_member_by_id(db, str(id))
    elif member_type == 'trainer':
        trainer = await crud.get_trainer_by_id(db, str(id))
    else:
        raise credentials_exception

    if member is None and trainer is None:
        raise credentials_exception
    return member or trainer

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

async def authenticate_member(db: AsyncSession, email: str, password: str):
    # Check member table
    member_result = await db.execute(select(models.Member).filter(models.Member.email == email))
    member = member_result.scalar_one_or_none()
    if member and verify_password(password, member.hashed_password):
        return member, 'member'
    
    # Check trainer table
    trainer_result = await db.execute(select(models.Trainer).filter(models.Trainer.email == email))
    trainer = trainer_result.scalar_one_or_none()
    if trainer and verify_password(password, trainer.hashed_password):
        return trainer, 'trainer'
    
    return None, None

async def admin_required(current_member: schemas.Member = Depends(get_current_user)):
    if current_member.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_member

def validate_password(password: str):
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    if not re.match(r'^[a-zA-Z0-9!@#$%^&*(),.?":{}|<>]+$', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password can only contain English letters, numbers, and special characters"
        )

    # Optional: Uncomment these if you want to enforce numbers and special characters
    # if not re.search(r'\d', password):
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Password must contain at least one number"
    #     )
    # 
    # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Password must contain at least one special character"
    #     )