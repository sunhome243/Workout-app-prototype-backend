# stats_service/utils.py

from fastapi import HTTPException, status
from fastapi.security import APIKeyHeader
import logging
import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError, InvalidTokenError
import os
import httpx

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
USER_SERVICE_URL = "http://localhost:8000"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define the API Key header scheme for Swagger UI
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

async def get_current_user(token: str = None):
    if token is None:
        return None

    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        logger.debug(f"Attempting to decode token: {token[:10]}...")  # Log first 10 characters of token for debugging

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug(f"Successfully decoded token. Payload: {payload}")

        member_id: str = payload.get("sub")
        role: str = payload.get("type")  # Changed to 'role' as per your token structure

        if member_id is None or role is None:
            logger.error(f"Invalid token payload: member_id={member_id}, role={role}")
            raise HTTPException(status_code=401, detail="Invalid token payload")

        logger.debug(f"Extracted from token: member_id={member_id}, role={role}")

        member_data = {
            "id": str(member_id),
            "user_type": role
        }

        logger.info(f"Member authenticated successfully: {member_data}")
        return member_data

    except ExpiredSignatureError:
        logger.error("Token has expired")
        raise HTTPException(status_code=401, detail="Token has expired")
    except InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except PyJWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid member ID format")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
    
async def get_member_me(token: str):
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": token}
        try:
            response = await client.get(f"{USER_SERVICE_URL}/api/members/me/", headers=headers)
            response.raise_for_status()
            user_data = response.json()
            logger.info(f"Received user data: {user_data}")
            return user_data
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred while fetching member data: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Error fetching member data: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error occurred while fetching member data: {str(e)}")
            raise HTTPException(status_code=500, detail="Unexpected error occurred")