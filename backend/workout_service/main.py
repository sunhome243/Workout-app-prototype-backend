from fastapi import FastAPI, Depends, HTTPException, Request, Header, Path, Query
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from sqlalchemy.ext.asyncio import AsyncSession
from backend.workout_service.database import get_db
from backend.workout_service import crud, schemas, utils
from unittest.mock import AsyncMock
from typing import List, Dict
from datetime import datetime
import logging
import httpx
import os

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

USER_SERVICE_URL = "http://127.0.0.1:8000"

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Workout Service API",
        version="1.0.0",
        description="API for managing workout sessions",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Enter your JWT token with the `Bearer ` prefix, e.g. `Bearer abcde12345`"
        }
    }
    openapi_schema["security"] = [{"Bearer": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/docs", include_in_schema=False)
async def get_documentation():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")

@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_json():
    return app.openapi()

@app.post("/api/create_session", response_model=schemas.SessionIDMap)
async def create_session(
    request: Request,
    session_type_id: int,
    member_id: str = Query(None),
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    try:
        current_member = await utils.get_current_user(authorization)
        logger.info(f"Current member: {current_member}")
        
        if current_member['user_type'] == 'trainer':
            if not member_id:
                raise HTTPException(status_code=400, detail="member_id is required for trainers")
            
            logger.info(f"Checking mapping for trainer {current_member.get('id')} and member {member_id}")
            mapping_exists = await crud.check_trainer_member_mapping(current_member.get('id'), member_id, authorization)
            logger.info(f"Mapping exists: {mapping_exists}")
            
            if not mapping_exists:
                raise HTTPException(status_code=403, detail="Trainer is not associated with this member")
            is_pt = True
        else:  # member
            if member_id and member_id != current_member.get('id'):
                raise HTTPException(status_code=403, detail="Member can only create sessions for themselves")
            member_id = current_member.get('id')
            is_pt = False
        
        session_data = {
            "member_id": member_id,
            "is_pt": is_pt,
            "session_type_id": session_type_id
        }
        
        logger.info(f"Creating session with data: {session_data}")
        new_session = await crud.create_session(db, session_data, current_member)
        logger.info(f"New session created: {new_session}")
        
        if session_type_id == 3 and is_pt:
            await crud.update_quests_status(db, member_id)
        
        return new_session
    except ValueError as ve:
        logger.error(f"Validation error in create_session: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as he:
        logger.error(f"HTTP exception in create_session: {str(he)}")
        raise he
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")

@app.post("/api/record_set", response_model=schemas.Session)
async def record_set_endpoint(
    session_id: int,
    workout_key: int,
    set_num: int,
    weight: float,
    reps: int,
    rest_time: int,
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    try:
        current_member = await utils.get_current_user(authorization)
        logger.debug(f"Member authenticated: {current_member}")
    except HTTPException as e:
        logger.error(f"Authentication error: {e.detail}")
        raise e

    try:
        logger.debug(f"Attempting to record set with data: session_id={session_id} workout_key={workout_key} set_num={set_num} weight={weight} reps={reps} rest_time={rest_time}")
        new_set = await crud.record_set(db, session_id, workout_key, set_num, weight, reps, rest_time)
        logger.info(f"Set recorded successfully: {new_set.session_id}")
        return new_set
    except ValueError as ve:
        logger.error(f"Validation error in record_set: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error recording set: {str(e)}")
        raise HTTPException(status_code=500, detail="Error recording set")



@app.get("/api/get_sessions/{member_id}", response_model=list[schemas.SessionWithSets])
async def get_sessions(
    member_id: str = Path(..., title="The ID of the member to get sessions for"),
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    try:
        current_member = await utils.get_current_user(authorization)
        member_id = current_member['id']
        user_type = current_member['user_type']
        logger.debug(f"Fetching sessions for member ID: {member_id}, current member ID: {member_id}, member type: {user_type}")
        
        if member_id != member_id:
            if user_type != 'trainer':
                raise HTTPException(status_code=403, detail="You don't have permission to access this member's sessions")
            # Check if the trainer is mapped to the requested member
            is_mapped = await crud.check_trainer_member_mapping(trainer_id=member_id, member_id=member_id, token=authorization)
            if not is_mapped:
                raise HTTPException(status_code=403, detail="You don't have permission to access this member's sessions")
        
        # Fetch sessions for the requested member_id
        sessions = await crud.get_sessions_by_member(db, member_id)
        if not sessions:
            logger.info(f"No sessions found for member ID: {member_id}")
            return []
        
        result = []
        for session in sessions:
            sets = await crud.get_sets_by_session(db, session.session_id)
            result.append(schemas.SessionWithSets(
                session_id=session.session_id,
                workout_date=session.workout_date,
                member_id=session.member_id,
                trainer_id=session.trainer_id,
                is_pt=session.is_pt,
                session_type_id=session.session_type_id,
                sets=[schemas.SetResponse(**set.__dict__) for set in sets]
            ))
        logger.info(f"Successfully fetched {len(result)} sessions for member ID: {member_id}")
        return result
    except HTTPException as he:
        logger.error(f"HTTP error in get_sessions: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Error fetching sessions: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching sessions")


@app.post("/api/create_quest", response_model=schemas.Quest)
async def create_quest_endpoint(
    quest_data: schemas.QuestCreate,
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    try:
        current_member = await utils.get_current_user(authorization)
        if current_member['user_type'] != 'trainer':
            raise HTTPException(status_code=403, detail="Only trainers can create quests")
        
        mapping_exists = await crud.check_trainer_member_mapping(current_member['id'], quest_data.member_id, authorization)
        if not mapping_exists:
            raise HTTPException(status_code=403, detail="Trainer is not associated with this member")
        
        new_quest = await crud.create_quest(db, quest_data, current_member['id'])
        return new_quest
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in create_quest: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
    
@app.get("/api/quests", response_model=List[schemas.Quest])
async def read_quests(
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    try:
        current_member = await utils.get_current_user(authorization)
        logger.debug(f"Current member: {current_member}")

        if current_member['user_type'] == 'trainer':
            quests = await crud.get_quests_by_trainer(db, current_member['id'])
        else:  # member
            quests = await crud.get_quests_by_member(db, current_member['id'])
        
        return quests
    except Exception as e:
        logger.error(f"Error reading quests: {str(e)}")
        raise HTTPException(status_code=500, detail="Error reading quests")

@app.get("/api/quests/{member_id}", response_model=List[schemas.Quest])
async def read_quests_for_member(
    member_id: str,
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    try:
        current_member = await utils.get_current_user(authorization)
        logger.debug(f"Current member: {current_member}")

        if current_member['user_type'] != 'trainer':
            raise HTTPException(status_code=403, detail="Only trainers can access this endpoint")

        # Check trainer-member mapping
        mapping_exists = await crud.check_trainer_member_mapping(current_member['id'], member_id, authorization)
        if not mapping_exists:
            raise HTTPException(status_code=403, detail="Trainer is not associated with this member")

        quests = await crud.get_quests_by_trainer_and_member(db, current_member['id'], member_id)
        
        return quests
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error reading quests for member: {str(e)}")
        raise HTTPException(status_code=500, detail="Error reading quests for member")

@app.patch("/api/quests/{quest_id}/status", response_model=schemas.Quest)
async def update_quest_status(
    quest_id: int = Path(..., title="The ID of the quest to update"),
    status: schemas.QuestStatus = Query(..., title="The new status of the quest"),
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    try:
        current_member = await utils.get_current_user(authorization)
        
        quest = await crud.get_quest_by_id(db, quest_id)
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found")
        
        if current_member['user_type'] == 'trainer' and quest.trainer_id != current_member['id']:
            raise HTTPException(status_code=403, detail="Not authorized to update this quest")
        elif current_member['user_type'] == 'member' and quest.member_id != current_member['id']:
            raise HTTPException(status_code=403, detail="Not authorized to update this quest")
        
        updated_quest = await crud.update_quest_status(db, quest_id, status)
        if not updated_quest:
            raise HTTPException(status_code=404, detail="Quest not found")
        
        return updated_quest
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error updating quest status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating quest status: {str(e)}")


@app.delete("/api/quests/{quest_id}", status_code=204)
async def delete_quest(
    quest_id: int = Path(..., title="The ID of the quest to delete"),
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    try:
        current_member = await utils.get_current_user(authorization)
        
        # Fetch the quest to check permissions
        quest = await crud.get_quest_by_id(db, quest_id)
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found")
        
        # Check if the member has permission to delete this quest
        if current_member['user_type'] == 'trainer' and quest.trainer_id != current_member['id']:
            raise HTTPException(status_code=403, detail="Not authorized to delete this quest")
        elif current_member['user_type'] == 'member' and quest.member_id != current_member['id']:
            raise HTTPException(status_code=403, detail="Members are not allowed to delete quests")
        
        # Delete the quest
        deleted = await crud.delete_quest(db, quest_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Quest not found")
        
        return None  # 204 No Content
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error deleting quest: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting quest: {str(e)}")
    
@app.get("/api/workout-records/{workout_key}", response_model=Dict[int, schemas.QuestWorkoutRecord])
async def get_workout_records(
    workout_key: int = Path(..., title="The workout key of the workout"),
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    try:
        current_member = await utils.get_current_user(authorization)
        
        records = await crud.get_workout_records(db, current_member['id'], workout_key)
        
        return records
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error retrieving workout records: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving workout records: {str(e)}")

@app.get("/api/workout-name/{workout_key}", response_model=schemas.WorkoutName)
async def get_workout_name(
    workout_key: int = Path(..., title="The workout key"),
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    try:
        await utils.get_current_user(authorization)  # Just to verify the member is authenticated
        
        workout_name = await crud.get_workout_name(db, workout_key)
        if workout_name is None:
            raise HTTPException(status_code=404, detail="Workout not found")
        
        return {"workout_key": workout_key, "workout_name": workout_name}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error retrieving workout name: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving workout name: {str(e)}")
    
    
@app.get("/api/workouts-by-part", response_model=Dict[str, List[schemas.WorkoutInfo]])
async def get_workouts_by_part(
    workout_part_id: int = Query(None, description="Optional: Filter by specific workout part ID"),
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    try:
        await utils.get_current_user(authorization)  # Just to verify the member is authenticated
        
        workouts_by_part = await crud.get_workouts_by_part(db, workout_part_id)
        return workouts_by_part
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error retrieving workouts by part: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving workouts by part: {str(e)}")

@app.get("/api/session_counts/{member_id}", response_model=Dict[str, int])
async def get_session_counts(
    member_id: str,
    start_date: datetime,
    end_date: datetime,
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    try:
        current_member = await utils.get_current_user(authorization)
        
        # Check if the current member is requesting their own data or if they're a trainer
        if current_member['id'] != member_id and current_member['user_type'] != 'trainer':
            raise HTTPException(status_code=403, detail="Not authorized to access this data")
        
        # If it's a trainer, check if they're mapped to the member
        if current_member['user_type'] == 'trainer':
            is_mapped = await crud.check_trainer_member_mapping(current_member['id'], member_id, authorization)
            if not is_mapped:
                raise HTTPException(status_code=403, detail="Not authorized to access this member's data")

        session_counts = await crud.get_session_counts(db, member_id, start_date, end_date)
        return session_counts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))