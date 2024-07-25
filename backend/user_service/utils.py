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

async def admin_required(current_user: models.Member = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

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