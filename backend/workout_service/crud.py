from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import update, delete, and_, func
from backend.workout_service import models, schemas
import logging
import httpx
from datetime import datetime
from aiocache import cached, caches
from aiocache.serializers import JsonSerializer
from collections import defaultdict
from fastapi import HTTPException
from typing import Union, List, Dict, Optional, Tuple
from firebase_admin import auth
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)

USER_SERVICE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

caches.set_config({
    'default': {
        'cache': "aiocache.SimpleMemoryCache",
        'serializer': {
            'class': "aiocache.serializers.JsonSerializer"
        }
    }
})

async def check_trainer_member_mapping(trainer_uid: str, member_uid: str, token: str):
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            url = f"{USER_SERVICE_URL}/api/check-trainer-member-mapping/{trainer_uid}/{member_uid}"
            logger.info(f"Checking trainer-member mapping: trainer_uid={trainer_uid}, member_uid={member_uid}")
            logger.debug(f"Sending request to: {url}")
            response = await client.get(url, headers=headers)
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response content: {response.text}")
            
            if response.status_code == 404:
                logger.warning(f"Mapping not found for trainer {trainer_uid} and member {member_uid}")
                return False
            
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Trainer-member mapping check result: {result}")
            mapping_exists = result.get("exists", False)
            logger.info(f"Mapping exists for trainer {trainer_uid} and member {member_uid}: {mapping_exists}")
            return mapping_exists
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred while checking trainer-member mapping: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Error checking trainer-member mapping: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error occurred while checking trainer-member mapping: {str(e)}")
            raise HTTPException(status_code=500, detail="Unexpected error occurred")

async def create_session(
    db: AsyncSession,
    session_type_id: Union[int, None],
    quest_id: Union[int, None],
    member_uid: Union[str, None],
    current_user: dict,
    token: str,
):
    try:
        if current_user['role'] == 'trainer':
            if not member_uid:
                raise ValueError("member_uid is required for trainers")
            
            mapping_exists = await check_trainer_member_mapping(current_user['uid'], member_uid, token)
            
            if not mapping_exists:
                raise HTTPException(status_code=403, detail="Trainer is not associated with this member")
            is_pt = True
            session_type_id = 3  # Always set session_type_id to 3 for trainers
            logger.info(f"Automatically set session_type_id to 3 for trainer {current_user['uid']}")
        else:  # member
            if member_uid and member_uid != current_user['uid']:
                raise HTTPException(status_code=403, detail="Member can only create sessions for themselves")
            member_uid = current_user['uid']
            is_pt = False
            if session_type_id is None:
                session_type_id = 3  # Default to 3 for custom workouts
                logger.info(f"Automatically set session_type_id to 3 for member {member_uid}")
        
        session_data = {
            "member_uid": member_uid,
            "trainer_uid": current_user['uid'] if current_user['role'] == 'trainer' else None,  
            "is_pt": is_pt,
            "session_type_id": session_type_id,
        }

        if session_type_id == 2:
            if quest_id is None:
                raise ValueError("quest_id is required for session_type_id 2")
            session_data["quest_id"] = quest_id
        elif quest_id is not None:
            raise ValueError("quest_id should only be provided for session_type_id 2")
        
        new_session = models.SessionIDMap(**session_data)
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        
        return new_session
    except ValueError as ve:
        logger.error(f"Validation error in create_session: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as he:
        logger.error(f"HTTP error in create_session: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in create_session: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")

async def save_session(db: AsyncSession, session_data: schemas.SessionSave, current_member: dict, authorization: str):
    logger.info(f"Starting save_session for session_id: {session_data.session_id}")
    
    async with db.begin() as transaction:
        try:
            session = await db.get(models.SessionIDMap, session_data.session_id)
            if not session:
                logger.error(f"Session not found: {session_data.session_id}")
                raise HTTPException(status_code=404, detail="Session not found")
            
            if session.member_uid != current_member['uid'] and current_member['role'] != 'trainer':
                logger.error(f"Unauthorized save attempt for session: {session_data.session_id}")
                raise HTTPException(status_code=403, detail="Not authorized to save this session")
            
            # Check if session has already been saved
            existing_sets = await db.execute(select(func.count()).select_from(models.Session).where(models.Session.session_id == session_data.session_id))
            existing_sets_count = existing_sets.scalar()
            
            if existing_sets_count > 0:
                logger.warning(f"Session {session_data.session_id} already has {existing_sets_count} sets. Deleting existing sets.")
                await db.execute(delete(models.Session).where(models.Session.session_id == session_data.session_id))
            
            # Add new exercises and sets
            for exercise in session_data.exercises:
                for set_data in exercise.sets:
                    new_set = models.Session(
                        session_id=session_data.session_id,
                        workout_key=exercise.workout_key,
                        set_num=set_data.set_num,
                        weight=set_data.weight,
                        reps=set_data.reps,
                        rest_time=set_data.rest_time
                    )
                    db.add(new_set)
            
            logger.info(f"Added {sum(len(exercise.sets) for exercise in session_data.exercises)} new sets for session {session_data.session_id}")
            
            if session.session_type_id == 2:  # Quest session
                quest = await db.get(models.Quest, session.quest_id)
                if quest:
                    quest.status = schemas.QuestStatus.COMPLETED
                    logger.info(f"Updated quest status to COMPLETED for quest_id: {session.quest_id}")
            
            if session.is_pt:
                await update_remaining_sessions(session.member_uid, session.trainer_uid, authorization)
                logger.info(f"Updated remaining sessions for PT session: {session_data.session_id}")
            
            await db.flush()
            await db.refresh(session)
            
            logger.info(f"Session {session_data.session_id} saved successfully")
            
            # Convert to Pydantic model for safe serialization
            response = schemas.SessionSaveResponse.from_orm(session)
            return response
        
        except Exception as e:
            logger.error(f"Error saving session {session_data.session_id}: {str(e)}")
            raise

async def update_remaining_sessions(member_uid: str, trainer_uid: str, token: str):
    async with httpx.AsyncClient() as client:
        try:
            url = f"{USER_SERVICE_URL}/user-service/trainer-member-mapping/{member_uid}/update-sessions"
            data = {"sessions_to_add": -1}  # Decrease by 1
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.patch(url, json=data, headers=headers)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Updated remaining sessions for member {member_uid} and trainer {trainer_uid}: {result}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred while updating remaining sessions: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Error updating remaining sessions: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error occurred while updating remaining sessions: {str(e)}")
            raise HTTPException(status_code=500, detail="Unexpected error occurred")

    
async def get_trainer_sessions(db: AsyncSession, trainer_uid: str):
    query = select(models.SessionIDMap).options(
        joinedload(models.SessionIDMap.sessions)
    ).filter_by(trainer_uid=trainer_uid)
    result = await db.execute(query)
    sessions = result.unique().scalars().all()
    
    return [schemas.SessionWithSets(
        session_id=session.session_id,
        workout_date=session.workout_date,
        member_uid=session.member_uid,
        trainer_uid=session.trainer_uid,
        is_pt=session.is_pt,
        session_type_id=session.session_type_id,
        sets=[schemas.SetResponse(
            session_id=set.session_id,
            workout_key=set.workout_key,
            set_num=set.set_num,
            weight=set.weight,
            reps=set.reps,
            rest_time=set.rest_time
        ) for set in session.sessions]
    ) for session in sessions]

async def get_sessions_by_member(db: AsyncSession, member_uid: str):
    query = select(models.SessionIDMap).options(
        joinedload(models.SessionIDMap.sessions)
    ).filter_by(member_uid=member_uid)
    result = await db.execute(query)
    sessions = result.unique().scalars().all()
    
    return [schemas.SessionWithSets(
        session_id=session.session_id,
        workout_date=session.workout_date,
        member_uid=session.member_uid,
        trainer_uid=session.trainer_uid,
        is_pt=session.is_pt,
        session_type_id=session.session_type_id,
        sets=[schemas.SetResponse(
            session_id=set.session_id,
            workout_key=set.workout_key,
            set_num=set.set_num,
            weight=set.weight,
            reps=set.reps,
            rest_time=set.rest_time
        ) for set in session.sessions]
    ) for session in sessions]
    
async def get_sets_by_session(db: AsyncSession, session_id: int):
    query = select(models.Session).filter_by(session_id=session_id)
    result = await db.execute(query)
    return result.scalars().all()

async def create_quest(db: AsyncSession, quest_data: schemas.QuestCreate, trainer_uid: str):
    try:
        new_quest = models.Quest(
            trainer_uid=trainer_uid,
            member_uid=quest_data.member_uid,
            status=models.QuestStatus.NOT_STARTED 
        )
        db.add(new_quest)
        await db.flush()

        for workout_data in quest_data.workouts:
            new_workout = models.QuestWorkout(
                quest_id=new_quest.quest_id,
                workout_key=workout_data.workout_key,
            )
            db.add(new_workout)
            await db.flush()

            for set_data in workout_data.sets:
                new_set = models.QuestWorkoutSet(
                    quest_id=new_quest.quest_id,
                    workout_key=new_workout.workout_key,
                    set_number=set_data.set_number,
                    weight=set_data.weight,
                    reps=set_data.reps,
                    rest_time=set_data.rest_time
                )
                db.add(new_set)

        await db.commit()

        # Reload the quest with all related data
        stmt = select(models.Quest).options(
            selectinload(models.Quest.workouts).selectinload(models.QuestWorkout.sets)
        ).where(models.Quest.quest_id == new_quest.quest_id)
        result = await db.execute(stmt)
        loaded_quest = result.scalar_one()

        logger.info(f"Quest created: {loaded_quest.quest_id}")
        return loaded_quest
    except Exception as e:
        logger.error(f"Error creating quest: {str(e)}")
        await db.rollback()
        raise


async def get_quests_by_trainer(db: AsyncSession, trainer_uid: str):
    stmt = select(models.Quest).options(
        selectinload(models.Quest.workouts).selectinload(models.QuestWorkout.sets)
    ).filter(models.Quest.trainer_uid == trainer_uid)
    result = await db.execute(stmt)
    return result.unique().scalars().all()

async def get_quests_by_member(db: AsyncSession, member_uid: str):
    stmt = select(models.Quest).options(
        selectinload(models.Quest.workouts).selectinload(models.QuestWorkout.sets)
    ).filter(models.Quest.member_uid == member_uid)
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_quests_by_trainer_and_member(db: AsyncSession, trainer_uid: str, member_uid: str):
    stmt = select(models.Quest).options(
        selectinload(models.Quest.workouts).selectinload(models.QuestWorkout.sets)
    ).filter(models.Quest.trainer_uid == trainer_uid, models.Quest.member_uid == member_uid)
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_quest_by_id(db: AsyncSession, quest_id: int):
    stmt = select(models.Quest).options(
        selectinload(models.Quest.workouts).selectinload(models.QuestWorkout.sets)
    ).filter(models.Quest.quest_id == quest_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def update_quests_status(db: AsyncSession, member_uid: str):
    try:
        stmt = update(models.Quest).where(
            (models.Quest.member_uid == member_uid) & 
            (models.Quest.status == models.QuestStatus.NOT_STARTED)
        ).values(status=models.QuestStatus.DEADLINE_PASSED)
        
        result = await db.execute(stmt)
        await db.commit()
        
        logger.info(f"Updated {result.rowcount} quests to 'Deadline passed' for member {member_uid}")
    except Exception as e:
        logger.error(f"Error updating quests status: {str(e)}")
        await db.rollback()
        raise

async def get_sessions_by_member(db: AsyncSession, member_uid: str):
    query = select(models.SessionIDMap).filter_by(member_uid=member_uid)
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    session_with_sets = []
    for session in sessions:
        sets = await get_sets_by_session(db, session.session_id)
        session_with_sets.append(schemas.SessionWithSets(
            session_id=session.session_id,
            workout_date=session.workout_date,
            member_uid=session.member_uid,
            trainer_uid=session.trainer_uid,
            is_pt=session.is_pt,
            session_type_id=session.session_type_id,
            sets=[schemas.SetResponse(**set.__dict__) for set in sets]
        ))
    
    return session_with_sets

async def delete_quest(db: AsyncSession, quest_id: int):
    try:
        # Delete associated QuestworkoutSets
        await db.execute(delete(models.QuestWorkoutSet).where(models.QuestWorkoutSet.quest_id == quest_id))

        # Delete associated Questworkouts
        await db.execute(delete(models.QuestWorkout).where(models.QuestWorkout.quest_id == quest_id))

        # Delete the Quest
        result = await db.execute(delete(models.Quest).where(models.Quest.quest_id == quest_id))
        await db.commit()

        if result.rowcount == 0:
            logger.info(f"No quest found with id {quest_id}")
            return False

        logger.info(f"Quest deleted: id={quest_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting quest: {str(e)}", exc_info=True)
        await db.rollback()
        raise
    
async def get_workout_records(db: AsyncSession, member_uid: str, workout_key: int):
    try:
        stmt = select(models.Quest, models.QuestWorkoutSet).join(
            models.QuestWorkout,
            and_(
                models.QuestWorkoutSet.quest_id == models.QuestWorkout.quest_id,
                models.QuestWorkoutSet.workout_key == models.QuestWorkout.workout_key
            )
        ).join(
            models.Quest,
            models.QuestWorkout.quest_id == models.Quest.quest_id
        ).where(
            and_(
                models.Quest.member_uid == member_uid,
                models.QuestWorkoutSet.workout_key == workout_key
            )
        ).order_by(models.Quest.created_at.desc(), models.QuestWorkoutSet.set_number)

        result = await db.execute(stmt)
        records = result.all()

        structured_records = defaultdict(lambda: {"date": None, "sets": []})
        
        for quest, workout_set in records:
            quest_id = quest.quest_id
            structured_records[quest_id]["date"] = quest.created_at
            structured_records[quest_id]["sets"].append({
                "set_number": workout_set.set_number,
                "weight": workout_set.weight,
                "reps": workout_set.reps,
                "rest_time": workout_set.rest_time
            })

        logger.info(f"Retrieved workout records for member {member_uid} and workout key {workout_key}")
        return dict(structured_records)
    except Exception as e:
        logger.error(f"Error retrieving workout records: {str(e)}", exc_info=True)
        raise
    
async def get_workout_name(db: AsyncSession, workout_key: int):
    try:
        stmt = select(models.WorkoutKeyNameMap).options(
            joinedload(models.WorkoutKeyNameMap.workout)
        ).where(models.WorkoutKeyNameMap.workout_key_id == workout_key)
        
        result = await db.execute(stmt)
        workout_key_map = result.scalar_one_or_none()
        
        if workout_key_map and workout_key_map.workout:
            return workout_key_map.workout.workout_name
        else:
            logger.warning(f"No workout found for workout_key: {workout_key}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving workout name: {str(e)}", exc_info=True)
        raise
    
async def get_workouts_by_part(db: AsyncSession, workout_part_id: int = None):
    try:
        stmt = select(models.WorkoutParts).options(
            joinedload(models.WorkoutParts.workout_keys).joinedload(models.WorkoutKeyNameMap.workout)
        )
        
        if workout_part_id:
            stmt = stmt.where(models.WorkoutParts.workout_part_id == workout_part_id)
        
        result = await db.execute(stmt)
        workout_parts = result.unique().scalars().all()
        
        workouts_by_part = {}
        for part in workout_parts:
            workouts = [
                {
                    "workout_key": key.workout_key_id,
                    "workout_name": key.workout.workout_name,
                    "workout_part": part.workout_part_name  # Add this line
                }
                for key in part.workout_keys
            ]
            workouts_by_part[part.workout_part_name] = workouts
        
        logger.info(f"Retrieved workouts by part{'s' if not workout_part_id else ''}")
        return workouts_by_part
    except Exception as e:
        logger.error(f"Error retrieving workouts by part: {str(e)}", exc_info=True)
        raise

async def get_session_counts(db: AsyncSession, member_uid: str, start_date: datetime, end_date: datetime):
    query = select(models.SessionIDMap).where(
        and_(
            models.SessionIDMap.member_uid == member_uid,
            models.SessionIDMap.workout_date >= start_date,
            models.SessionIDMap.workout_date < end_date
        )
    )
    result = await db.execute(query)
    sessions = result.scalars().all()

    counts = {
        'ai_sessions': 0,
        'custom_sessions': 0,
        'quest_sessions': 0,
        'pt_sessions': 0
    }

    for session in sessions:
        if session.session_type_id == 1 and not session.is_pt:
            counts['ai_sessions'] += 1
        elif session.session_type_id == 3 and not session.is_pt:
            counts['custom_sessions'] += 1
        elif session.session_type_id == 2 and not session.is_pt:
            counts['quest_sessions'] += 1
        elif session.session_type_id == 3 and session.is_pt:
            counts['pt_sessions'] += 1

    return counts

async def get_last_session_update(db: AsyncSession, uie: str) -> datetime:
    query = select(func.max(models.SessionIDMap.workout_date)).where(models.SessionIDMap.member_uid == uid)
    result = await db.execute(query)
    last_updated = result.scalar_one_or_none()
    return last_updated or datetime.min

async def search_workouts(db: AsyncSession, workout_name: str):
    try:
        stmt = select(models.WorkoutKeyNameMap).options(
            joinedload(models.WorkoutKeyNameMap.workout),
            joinedload(models.WorkoutKeyNameMap.workout_part)
        ).join(models.Workouts).where(
            func.lower(models.Workouts.workout_name).contains(func.lower(workout_name.replace(' ', '%')))
        )
        
        result = await db.execute(stmt)
        workout_key_maps = result.unique().scalars().all()
        
        if not workout_key_maps:
            logger.warning(f"No workouts found for search term: {workout_name}")
            return []

        workouts = [
            {
                "workout_key": wkm.workout_key_id,
                "workout_name": wkm.workout.workout_name,
                "workout_part": wkm.workout_part.workout_part_name
            }
            for wkm in workout_key_maps
        ]
        
        logger.info(f"Found {len(workouts)} workouts for search term: {workout_name}")
        return workouts
    except Exception as e:
        logger.error(f"Error searching workouts: {str(e)}", exc_info=True)
        raise
    
async def get_trainer_name(token: str, trainer_uid: str):
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            url = f"{USER_SERVICE_URL}/user-service/trainers/byuid/{trainer_uid}"
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            trainer_data = response.json()
            return f"{trainer_data['first_name']} {trainer_data['last_name']}"
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred while fetching trainer name: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error occurred while fetching trainer name: {str(e)}")
            return None

async def get_session_detail(db: AsyncSession, session_id: int, token: str):
    try:
        stmt = select(models.SessionIDMap).options(
            joinedload(models.SessionIDMap.sessions).joinedload(models.Session.workout_key_name_map).joinedload(models.WorkoutKeyNameMap.workout),
            joinedload(models.SessionIDMap.sessions).joinedload(models.Session.workout_key_name_map).joinedload(models.WorkoutKeyNameMap.workout_part)
        ).where(models.SessionIDMap.session_id == session_id)

        result = await db.execute(stmt)
        session = result.unique().scalar_one_or_none()

        if not session:
            return None

        workouts = {}
        for set_data in session.sessions:
            workout_key = set_data.workout_key
            if workout_key not in workouts:
                workouts[workout_key] = {
                    "workout_key": workout_key,
                    "workout_name": set_data.workout_key_name_map.workout.workout_name,
                    "workout_part": set_data.workout_key_name_map.workout_part.workout_part_name,
                    "sets": []
                }
            workouts[workout_key]["sets"].append({
                "set_num": set_data.set_num,
                "weight": set_data.weight,
                "reps": set_data.reps,
                "rest_time": set_data.rest_time
            })

        session_type = await db.execute(select(models.SessionTypeMap).where(models.SessionTypeMap.session_type_id == session.session_type_id))
        session_type = session_type.scalar_one_or_none()

        trainer_name = None
        if session.trainer_uid:
            trainer_name = await get_trainer_name(token, session.trainer_uid)

        return schemas.SessionDetail(
            session_id=session.session_id,
            workout_date=session.workout_date,
            member_uid=session.member_uid,
            trainer_uid=session.trainer_uid,
            trainer_name=trainer_name,
            is_pt=session.is_pt,
            session_type_id=session.session_type_id,
            session_type=session_type.session_type if session_type else "Unknown",
            workouts=[schemas.WorkoutDetail(**workout) for workout in workouts.values()]
        )
    except Exception as e:
        logging.error(f"Error getting session detail: {str(e)}", exc_info=True)
        raise