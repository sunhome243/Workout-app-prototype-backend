from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import update
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

@cached(ttl=3000, key="trainer_user_mapping:{trainer_id}:{user_id}")
async def check_trainer_user_mapping(trainer_id: str, user_id: str, token: str):
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": token}
        try:
            url = f"{USER_SERVICE_URL}/check-trainer-user-mapping/{trainer_id}/{user_id}"
            logger.debug(f"Sending request to: {url}")
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Trainer-user mapping check result: {result}")
            mapping_exists = result.get("exists", False)
            logger.info(f"Mapping exists for trainer {trainer_id} and user {user_id}: {mapping_exists}")
            return mapping_exists
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

async def create_quest(db: AsyncSession, quest_data: schemas.QuestCreate, trainer_id: str):
    try:
        new_quest = models.Quest(
            trainer_id=trainer_id,
            user_id=quest_data.user_id,
            status=False
        )
        db.add(new_quest)
        await db.flush()

        for exercise_data in quest_data.exercises:
            new_exercise = models.QuestExercise(
                quest_id=new_quest.quest_id,
                workout_key=exercise_data.workout_key,
            )
            db.add(new_exercise)
            await db.flush()

            for set_data in exercise_data.sets:
                new_set = models.QuestExerciseSet(
                    quest_id=new_quest.quest_id,
                    workout_key=new_exercise.workout_key,
                    set_number=set_data.set_number,
                    weight=set_data.weight,
                    reps=set_data.reps,
                    rest_time=set_data.rest_time
                )
                db.add(new_set)

        await db.commit()

        # Reload the quest with all related data
        stmt = select(models.Quest).options(
            selectinload(models.Quest.exercises).selectinload(models.QuestExercise.sets)
        ).where(models.Quest.quest_id == new_quest.quest_id)
        result = await db.execute(stmt)
        loaded_quest = result.scalar_one()

        logger.info(f"Quest created: {loaded_quest.quest_id}")
        return loaded_quest
    except Exception as e:
        logger.error(f"Error creating quest: {str(e)}")
        await db.rollback()
        raise


async def get_quests_by_trainer(db: AsyncSession, trainer_id: str):
    stmt = select(models.Quest).options(
        selectinload(models.Quest.exercises).selectinload(models.QuestExercise.sets)
    ).filter(models.Quest.trainer_id == trainer_id)
    result = await db.execute(stmt)
    return result.unique().scalars().all()

async def get_quests_by_user(db: AsyncSession, user_id: str):
    stmt = select(models.Quest).options(
        selectinload(models.Quest.exercises).selectinload(models.QuestExercise.sets)
    ).filter(models.Quest.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_quests_by_trainer_and_user(db: AsyncSession, trainer_id: str, user_id: str):
    stmt = select(models.Quest).options(
        selectinload(models.Quest.exercises).selectinload(models.QuestExercise.sets)
    ).filter(models.Quest.trainer_id == trainer_id, models.Quest.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_quest_by_id(db: AsyncSession, quest_id: int):
    stmt = select(models.Quest).options(
        selectinload(models.Quest.exercises).selectinload(models.QuestExercise.sets)
    ).filter(models.Quest.quest_id == quest_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def update_quest_status(db: AsyncSession, quest_id: int, new_status: bool):
    try:
        stmt = update(models.Quest).where(models.Quest.quest_id == quest_id).values(status=new_status)
        await db.execute(stmt)
        await db.commit()

        # Fetch the updated quest
        stmt = select(models.Quest).options(
            selectinload(models.Quest.exercises).selectinload(models.QuestExercise.sets)
        ).where(models.Quest.quest_id == quest_id)
        result = await db.execute(stmt)
        updated_quest = result.scalar_one_or_none()

        if updated_quest is None:
            logger.error(f"Quest with id {quest_id} not found")
            return None

        logger.info(f"Quest status updated: id={quest_id}, new_status={new_status}")
        return updated_quest
    except Exception as e:
        logger.error(f"Error updating quest status: {str(e)}")
        await db.rollback()
        raise