from firebase_admin import auth
from cachetools import TTLCache
from datetime import timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import httpx
from dotenv import load_dotenv
import os 

load_dotenv()
# User Service URL
USER_SERVICE_URL = os.getenv("SQLALCHEMY_DATABASE_URL") 

# 토큰 검증 결과를 캐시하기 위한 TTLCache 설정
token_cache = TTLCache(maxsize=1000, ttl=timedelta(minutes=5).total_seconds())
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='app.log', filemode='a')
logger = logging.getLogger(__name__)

async def verify_token(token: str):
    if token in token_cache:
        return token_cache[token]
    
    try:
        decoded_token = auth.verify_id_token(token)
        token_cache[token] = decoded_token
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials", headers={"WWW-Authenticate": "Bearer"})

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        decoded_token = await verify_token(token)
        uid = decoded_token.get("uid")
        user_type = decoded_token.get("role")
        
        logging.info(f"Decoded token: {decoded_token}")
        logging.info(f"UID from token: {uid}")
        logging.info(f"User type from token: {user_type}")
        
        if uid is None or user_type is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # User Service API를 호출하여 사용자 정보 가져오기
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{USER_SERVICE_URL}/api/{user_type}s/byuid/{uid}", headers={"Authorization": f"Bearer {token}"})
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="User not found or unauthorized")
        
        user_data = response.json()
        logging.info(f"User data from User Service: {user_data}")
        
        return user_data, user_type
    except Exception as e:
        logging.error(f"Error in get_current_user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=401, detail=str(e))