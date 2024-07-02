from datetime import datetime, timedelta
from typing import Optional, Annotated
import jwt
from jwt.exceptions import InvalidTokenError
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import pytz

from . import schemas, crud
from .database import SessionLocal, engine, get_db

# JWT 설정
SECRET_KEY = "LcdBKEBUqF3F12SFU0JhP0061PXJGQUp"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 20

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(pytz.utc) + expires_delta
    else:
        expire = datetime.now(pytz.utc) + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = crud.get_user_by_email(db, email=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
):
    return current_user

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def authenticate_user(db: Session, email: str, password: str):
    user = crud.get_user_by_email(db, email)
    if user and verify_password(password, user.hashed_password):
        return user
    
    trainer = crud.get_trainer_by_email(db, email)
    if trainer and verify_password(password, trainer.hashed_password):
        return trainer
    
    return False

