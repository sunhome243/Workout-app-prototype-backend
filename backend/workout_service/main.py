from fastapi import FastAPI, Depends, HTTPException, Request, Header, Path, Query
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from sqlalchemy.ext.asyncio import AsyncSession
from backend.workout_service.database import get_db
from backend.workout_service import crud, schemas, utils
from firebase_admin_init import initialize_firebase
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from datetime import datetime
import logging
import httpx
from firebase_admin import auth, credentials
import firebase_admin

initialize_firebase()

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log',  # 로그를 파일에 저장
    filemode='a'  # 로그를 추가 모드로 저장
)
logger = logging.getLogger(__name__)

# 콘솔에도 로그 출력
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

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
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
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

async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.post("/api/create_session", response_model=schemas.SessionIDMap)
async def create_session_endpoint(
    request: Request,
    session_type_id: Optional[int] = Query(None, description="Session type ID. If not provided, it will be automatically set based on user type."),
    quest_id: Optional[int] = Query(None, description="Quest ID. Required for session_type_id 2."),
    member_uid: Optional[str] = Query(None, description="Member ID. Required for trainers."),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Parse the request body as JSON
        body = await request.json()
        
        # Override query parameters with values from the body if provided
        if "session_type_id" in body and body["session_type_id"] is not None:
            session_type_id = body["session_type_id"]
        if "quest_id" in body and body["quest_id"] is not None:
            quest_id = body["quest_id"]
        if "member_uid" in body and body["member_uid"] is not None:
            member_uid = body["member_uid"]

        # Get the token from headers
        token = request.headers.get('Authorization').split(" ")[1]
        
        if session_type_id is None:
            session_type_id = 3  # Default to 3 for custom workouts
        
        # Call the CRUD function to create the session
        new_session = await crud.create_session(
            db, 
            session_type_id, 
            quest_id, 
            member_uid, 
            current_user, 
            token
        )
        return new_session
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")
    
@app.get("/api/get_oldest_not_started_quest", response_model=schemas.Quest)
async def get_oldest_not_started_quest(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        quest = await crud.get_oldest_not_started_quest(db, current_user['uid'])
        if not quest:
            raise HTTPException(status_code=404, detail="No not started quests found")
        return quest
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching oldest not started quest: {str(e)}")

@app.post("/api/save_session", response_model=schemas.SessionSaveResponse)
async def save_session(
    request: Request,
    session_data: schemas.SessionSave,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        token = request.headers.get('Authorization').split(" ")[1]
        updated_session = await crud.save_session(db, session_data, current_user, token)
        return updated_session
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving session: {str(e)}")

@app.get("/api/get_sessions/{member_uid}", response_model=List[schemas.SessionWithSets])
async def get_sessions(
    request: Request,
    member_uid: str = Path(..., title="The ID of the member to get sessions for"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_type = current_user['role']
        logger.debug(f"Fetching sessions for member ID: {member_uid}, current user ID: {current_user['uid']}, user type: {user_type}")
        
        if member_uid != current_user['uid']:
            if user_type != 'trainer':
                raise HTTPException(status_code=403, detail="You don't have permission to access this member's sessions")
            # Check if the trainer is mapped to the requested member
            token = request.headers.get('Authorization').split(" ")[1]
            is_mapped = await crud.check_trainer_member_mapping(trainer_uid=current_user['uid'], member_uid=member_uid, token=token)
            if not is_mapped:
                raise HTTPException(status_code=403, detail="You don't have permission to access this member's sessions")
        
        # Fetch sessions for the requested member_uid
        sessions = await crud.get_sessions_by_member(db, member_uid)
        if not sessions:
            logger.info(f"No sessions found for member ID: {member_uid}")
            return []
        
        result = []
        for session in sessions:
            sets = await crud.get_sets_by_session(db, session.session_id)
            result.append(schemas.SessionWithSets(
                session_id=session.session_id,
                workout_date=session.workout_date,
                member_uid=session.member_uid,
                trainer_uid=session.trainer_uid,
                is_pt=session.is_pt,
                session_type_id=session.session_type_id,
                sets=[schemas.SetResponse(**set.__dict__) for set in sets]
            ))
        logger.info(f"Successfully fetched {len(result)} sessions for member ID: {member_uid}")
        return result
    except HTTPException as he:
        logger.error(f"HTTP error in get_sessions: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Error fetching sessions: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching sessions")

@app.post("/api/create_quest", response_model=schemas.Quest)
async def create_quest_endpoint(
    request: Request,
    quest_data: schemas.QuestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        if current_user['role'] != 'trainer':
            raise HTTPException(status_code=403, detail="Only trainers can create quests")
        
        token = request.headers.get('Authorization').split(" ")[1]
        mapping_exists = await crud.check_trainer_member_mapping(current_user['uid'], quest_data.member_uid, token)
        if not mapping_exists:
            raise HTTPException(status_code=403, detail="Trainer is not associated with this member")
        
        new_quest = await crud.create_quest(db, quest_data, current_user['uid'])
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
    current_user: dict = Depends(get_current_user)
):
    try:
        logger.debug(f"Current user: {current_user}")

        if current_user['role'] == 'trainer':
            quests = await crud.get_quests_by_trainer(db, current_user['uid'])
        else:  # member
            quests = await crud.get_quests_by_member(db, current_user['uid'])
        
        return quests
    except Exception as e:
        logger.error(f"Error reading quests: {str(e)}")
        raise HTTPException(status_code=500, detail="Error reading quests")

@app.get("/api/quests/{member_uid}", response_model=List[schemas.Quest])
async def read_quests_for_member(
    request: Request,
    member_uid: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        logger.debug(f"Current user: {current_user}")

        if current_user['role'] != 'trainer':
            raise HTTPException(status_code=403, detail="Only trainers can access this endpoint")

        # Check trainer-member mapping
        token = request.headers.get('Authorization').split(" ")[1]
        mapping_exists = await crud.check_trainer_member_mapping(current_user['uid'], member_uid, token)
        if not mapping_exists:
            raise HTTPException(status_code=403, detail="Trainer is not associated with this member")

        quests = await crud.get_quests_by_trainer_and_member(db, current_user['uid'], member_uid)
        
        return quests
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error reading quests for member: {str(e)}")
        raise HTTPException(status_code=500, detail="Error reading quests for member")

@app.delete("/api/quests/{quest_id}", status_code=204)
async def delete_quest(
    quest_id: int = Path(..., title="The ID of the quest to delete"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Fetch the quest to check permissions
        quest = await crud.get_quest_by_id(db, quest_id)
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found")
        
        # Check if the user has permission to delete this quest
        if current_user['role'] == 'trainer' and quest.trainer_uid != current_user['uid']:
            raise HTTPException(status_code=403, detail="Not authorized to delete this quest")
        elif current_user['role'] == 'member' and quest.member_uid != current_user['uid']:
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
    current_user: dict = Depends(get_current_user)
):
    try:
        records = await crud.get_workout_records(db, current_user['uid'], workout_key)
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
    current_user: dict = Depends(get_current_user)
):
    try:
        workout_name = await crud.get_workout_name(db, workout_key)
        if workout_name is None:
            raise HTTPException(status_code=404, detail="Workout not found")
        
        return {"workout_key": workout_key, "workout_name": workout_name}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error retrieving workout name: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving workout name: {str(e)}")

@app.get("/api/search-workouts", response_model=List[schemas.WorkoutInfo])
async def search_workouts(
    workout_name: str = Query(..., description="The name of the workout to search for"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        workouts = await crud.search_workouts(db, workout_name)
        if not workouts:
            raise HTTPException(status_code=404, detail="No workouts found")
        
        return workouts
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error searching workouts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error searching workouts: {str(e)}")

@app.get("/api/workouts-by-part", response_model=Dict[str, List[schemas.WorkoutInfo]])
async def get_workouts_by_part(
    workout_part_id: int = Query(None, description="Optional: Filter by specific workout part ID"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        workouts_by_part = await crud.get_workouts_by_part(db, workout_part_id)
        return workouts_by_part
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error retrieving workouts by part: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving workouts by part: {str(e)}")

@app.get("/api/session_counts/{member_uid}", response_model=Dict[str, int])
async def get_session_counts(
    request: Request,
    member_uid: str,
    start_date: datetime,
    end_date: datetime,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Check if the current user is requesting their own data or if they're a trainer
        if current_user['uid'] != member_uid and current_user['role'] != 'trainer':
            raise HTTPException(status_code=403, detail="Not authorized to access this data")
        
        # If it's a trainer, check if they're mapped to the member
        if current_user['role'] == 'trainer':
            token = request.headers.get('Authorization').split(" ")[1]
            is_mapped = await crud.check_trainer_member_mapping(current_user['uid'], member_uid, token)
            if not is_mapped:
                raise HTTPException(status_code=403, detail="Not authorized to access this member's data")

        session_counts = await crud.get_session_counts(db, member_uid, start_date, end_date)
        return session_counts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/last-session-update/{uid}")
async def get_last_session_update(
    uid: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        if current_user['uid'] != uid and current_user['role'] != 'trainer':
            raise HTTPException(status_code=403, detail="Not authorized to access this data")
        
        last_updated = await crud.get_last_session_update(db, uid)
        return {"last_updated": last_updated.isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)