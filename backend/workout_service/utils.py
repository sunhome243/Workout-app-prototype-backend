from fastapi import HTTPException, status
import httpx
import os
import logging
import jwt
from jwt.exceptions import PyJWTError

USER_SERVICE_URL = "http://127.0.0.1:8000"
SECRET_KEY = os.getenv("SECRET_KEY")  # Make sure this matches the secret key used in user_service

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def get_current_member(token: str):
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        user_type: str = payload.get("type")
        
        if email is None or user_type is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        logger.debug(f"Decoded token payload: email={email}, user_type={user_type}")

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            if user_type == 'user':
                response = await client.get(f"{USER_SERVICE_URL}/users/byemail/{email}", headers=headers)
            elif user_type == 'trainer':
                response = await client.get(f"{USER_SERVICE_URL}/trainers/byemail/{email}", headers=headers)
            else:
                logger.error(f"Invalid user_type: {user_type}")
                raise HTTPException(status_code=400, detail="Invalid user type")
            
            response.raise_for_status()
            user_data = response.json()
            
            # Add user_type to the user_data
            user_data['user_type'] = user_type
            
            logger.info(f"User authenticated successfully: {user_data}")
            return user_data

    except PyJWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e}")
        if e.response.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")