import os
from typing import Union
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
import httpx
from . import schemas

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=USER_SERVICE_URL + "/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{USER_SERVICE_URL}/current_user", headers={"Authorization": f"Bearer {token}"})
            if response.status_code == 200:
                user_data = response.json()
                if user_data.get("type") == "user":
                    user = schemas.User(**user_data)
                elif user_data.get("type") == "trainer":
                    user = schemas.Trainer(**user_data)
                else:
                    raise credentials_exception
                return user
            else:
                raise credentials_exception
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to user service"
        )

def get_current_trainer(current_user: Union[schemas.User, schemas.Trainer] = Depends(get_current_user)):
    if not isinstance(current_user, schemas.Trainer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

def trainer_required(current_user: Union[schemas.User, schemas.Trainer] = Depends(get_current_user)):
    if not isinstance(current_user, schemas.Trainer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only trainers can perform this action"
        )
    return current_user

async def get_user_trainer_relationship(user_id: int, trainer_id: int):
    cache_key = f"relationship_{user_id}_{trainer_id}"
    if cache_key in user_cache:
        return user_cache[cache_key]

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{USER_SERVICE_URL}/trainer-user-mapping/{trainer_id}/{user_id}")
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trainer-user relationship not found"
            )
        relationship = response.json()
        user_cache[cache_key] = relationship
        return relationship

# Function to clear cache for a specific user (useful when user data is updated)
def clear_user_cache(email: str):
    if email in user_cache:
        del user_cache[email]