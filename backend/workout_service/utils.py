from fastapi import HTTPException, status
import logging
import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError, InvalidTokenError
import os

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def get_current_member(token: str):
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        logger.debug(f"Attempting to decode token: {token[:10]}...") # Log first 10 characters of token for debugging

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug(f"Successfully decoded token. Payload: {payload}")

        user_id: str = payload.get("sub")
        role: str = payload.get("type")  # Changed to 'role' as per your token structure

        if user_id is None or role is None:
            logger.error(f"Invalid token payload: user_id={user_id}, role={role}")
            raise HTTPException(status_code=401, detail="Invalid token payload")

        logger.debug(f"Extracted from token: user_id={user_id}, role={role}")

        user_data = {
            "id": str(user_id),  # Convert to int as it's stored as string in the token
            "user_type": role
        }

        logger.info(f"User authenticated successfully: {user_data}")
        return user_data

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
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

def is_token_valid(token: str) -> bool:
    try:
        if token.startswith('Bearer '):
            token = token[7:]
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return True
    except PyJWTError:
        return False

# You can add a function to print the token contents for debugging
def print_token_contents(token: str):
    try:
        if token.startswith('Bearer '):
            token = token[7:]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_signature": False})
        logger.debug(f"Token contents (without verification): {payload}")
    except Exception as e:
        logger.error(f"Error decoding token contents: {str(e)}")