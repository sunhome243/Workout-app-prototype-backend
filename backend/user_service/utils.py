from firebase_admin import auth
from cachetools import TTLCache
from datetime import timedelta
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from .database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud


# 토큰 검증 결과를 캐시하기 위한 TTLCache 설정
# 최대 1000개의 항목을 저장하고, 각 항목은 5분 동안 유효
token_cache = TTLCache(maxsize=1000, ttl=timedelta(minutes=5).total_seconds())
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def verify_token(token: str):
    if token in token_cache:
        return token_cache[token]
    
    try:
        decoded_token = auth.verify_id_token(token)
        # 캐시에 검증된 토큰 정보 저장
        token_cache[token] = decoded_token
        return decoded_token
    except Exception as e:
        # 토큰 검증 실패 시 예외 처리
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    try:
        decoded_token = await verify_token(token)
        uid = decoded_token.get("uid")
        user_type = decoded_token.get("role")
        
        if uid is None or user_type is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # 사용자 정보 데이터베이스에서 조회
        if user_type == 'member':
            user = await crud.get_member_by_uid(db, str(uid))
        elif user_type == 'trainer':
            user = await crud.get_trainer_by_uid(db, str(uid))
        else:
            raise HTTPException(status_code=401, detail="Invalid user type")
        
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user, user_type
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))