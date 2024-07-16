from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.workout_service import models, schemas
import logging
import httpx
from datetime import datetime
from aiocache import cached, caches
from aiocache.serializers import JsonSerializer

logger = logging.getLogger(__name__)

USER_SERVICE_URL = "http://127.0.0.1:8000"

caches.set_config({
    'default': {
        'cache': "aiocache.SimpleMemoryCache",
        'serializer': {
            'class': "aiocache.serializers.JsonSerializer"
        }
    }
})

@cached(ttl=300, key="trainer_user_mapping:{trainer_id}:{user_id}")
async def check_trainer_user_mapping(trainer_id: str, user_id: str, token: str):
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": token}
        try:
            response = await client.get(f"{USER_SERVICE_URL}/check-trainer-user-mapping/{trainer_id}/{user_id}", headers=headers)
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Trainer-user mapping check result: {result}")
            return result.get("exists", False)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred while checking trainer-user mapping: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Error checking trainer-user mapping: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error occurred while checking trainer-user mapping: {str(e)}")
            raise HTTPException(status_code=500, detail="Unexpected error occurred")




async def create_session(db: AsyncSession, session_data: dict, current_user: dict):
    try:
        # Ensure required fields are in the session_data
        required_fields = ['session_type_id', 'user_id', 'is_pt']
        for field in required_fields:
            if field not in session_data:
                raise ValueError(f"{field} is required")

        # Validate and convert session_type_id to integer
        try:
            session_type_id = int(session_data['session_type_id'])
        except ValueError:
            raise ValueError("session_type_id must be a valid integer")

        # Create session data
        session_data_to_create = {
            "workout_date": session_data.get('workout_date', datetime.now().strftime("%Y-%m-%d")),
            "user_id": session_data['user_id'],
            "trainer_id": current_user.get('id'),
            "is_pt": session_data['is_pt'],
            "session_type_id": session_type_id
        }

        # Create a new SessionIDMap instance
        new_session = models.SessionIDMap(**session_data_to_create)

        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)

        logger.info(f"Session created: {new_session.session_id}")
        return new_session
    except ValueError as ve:
        logger.error(f"Validation error in create_session: {str(ve)}")
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        await db.rollback()
        raise
    
async def record_set(db: AsyncSession, session_id: int, workout_key: int, set_num: int, weight: float, reps: int, rest_time: int):
    try:
        # Check if the workout_key exists
        workout_key_query = select(models.WorkoutKeyNameMap).filter_by(workout_key_id=workout_key)
        workout_key_result = await db.execute(workout_key_query)
        workout_key_map = workout_key_result.scalar_one_or_none()
        
        if not workout_key_map:
            raise ValueError(f"Invalid workout_key: {workout_key}")

        # Create new set record
        new_set = models.Session(
            session_id=session_id,
            workout_key=workout_key,
            set_num=set_num,
            weight=weight,
            reps=reps,
            rest_time=rest_time
        )

        db.add(new_set)
        await db.commit()
        await db.refresh(new_set)

        logger.info(f"Set recorded: session_id={session_id}, workout_key={workout_key}, set_num={set_num}")
        return new_set
    except Exception as e:
        logger.error(f"Error recording set: {str(e)}")
        await db.rollback()
        raise
    
async def get_sessions_by_user(db: AsyncSession, user_id: str):
    query = select(models.SessionIDMap).filter_by(user_id=user_id)
    result = await db.execute(query)
    return result.scalars().all()

async def get_sets_by_session(db: AsyncSession, session_id: int):
    query = select(models.Session).filter_by(session_id=session_id)
    result = await db.execute(query)
    return result.scalars().all()
