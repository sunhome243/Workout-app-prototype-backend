from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from firebase_admin import auth
from . import crud, models
from .database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        decoded_token = auth.verify_id_token(token)
        uid: str = decoded_token.get("uid")
        user_type: str = decoded_token.get("role")
        if uid is None or user_type is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    user = None
    if user_type == 'member':
        user = await crud.get_member_by_uid(db, str(uid))
    elif user_type == 'trainer':
        user = await crud.get_trainer_by_uid(db, str(uid))
    else:
        raise credentials_exception

    if user is None:
        raise credentials_exception
    return user

# You can add a function to print the token contents for debugging
def print_token_contents(token: str):
    try:
        if token.startswith('Bearer '):
            token = token[7:]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_signature": False})
        logger.debug(f"Token contents (without verification): {payload}")
    except Exception as e:
        logger.error(f"Error decoding token contents: {str(e)}")