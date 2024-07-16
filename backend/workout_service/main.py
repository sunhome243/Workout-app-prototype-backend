from fastapi import FastAPI, Depends, HTTPException, Request, Header, Path, Query
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from sqlalchemy.ext.asyncio import AsyncSession
from backend.workout_service.database import get_db
from backend.workout_service import crud, schemas, utils
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

@app.post("/create_session", response_model=schemas.SessionIDMap)
async def create_session(
    request: Request,
    session_type_id: str,
    user_id: str = Query(None),
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    logger.debug(f"Received request headers for create_session: {request.headers}")
    logger.debug(f"Attempting to authenticate with token: {authorization[:10]}...")
    
    utils.print_token_contents(authorization)
    
    try:
        current_user = await utils.get_current_member(authorization)
        logger.debug(f"Authentication successful. Current user: {current_user}")
    except HTTPException as e:
        logger.error(f"Authentication error: {e.detail}")
        raise e
    
    try:
        if current_user['user_type'] == 'trainer':
            if not user_id:
                raise HTTPException(status_code=400, detail="user_id is required for trainers")
            
            logger.debug(f"Checking trainer-user mapping for trainer_id={current_user.get('id')} and user_id={user_id}")
            mapping_exists = await crud.check_trainer_user_mapping(current_user.get('id'), user_id, authorization)
            logger.debug(f"Mapping exists: {mapping_exists}")
            if not mapping_exists:
                raise HTTPException(status_code=403, detail="Trainer is not associated with this user")
            is_pt = "Y"
        else:  # user
            if user_id and user_id != current_user.get('id'):
                raise HTTPException(status_code=403, detail="User can only create sessions for themselves")
            user_id = current_user.get('id')
            is_pt = "N"
        
        session_data = {
            "user_id": user_id,
            "is_pt": is_pt,
            "session_type_id": session_type_id
        }
        
        logger.debug(f"Attempting to create session with data: {session_data}")
        new_session = await crud.create_session(db, session_data, current_user)
        logger.info(f"Session created successfully: {new_session.session_id}")
        return new_session
    except ValueError as ve:
        logger.error(f"Validation error in create_session: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as he:
        logger.error(f"HTTP exception in create_session: {str(he)}")
        raise he
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating session")


@app.post("/record_set", response_model=schemas.Session)
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
        current_user = await utils.get_current_member(authorization)
        logger.debug(f"User authenticated: {current_user}")
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



@app.get("/get_sessions/{member_id}", response_model=list[schemas.SessionWithSets])
async def get_sessions(
    member_id: str = Path(..., title="The ID of the member to get sessions for"),
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    try:
        current_user = await utils.get_current_member(authorization)
        user_id = current_user['id']
        user_type = current_user['user_type']
        logger.debug(f"Fetching sessions for member ID: {member_id}, current user ID: {user_id}, user type: {user_type}")
        
        if user_id != member_id:
            if user_type != 'trainer':
                raise HTTPException(status_code=403, detail="You don't have permission to access this member's sessions")
            # Check if the trainer is mapped to the requested user
            is_mapped = await crud.check_trainer_user_mapping(trainer_id=user_id, user_id=member_id, token=authorization)
            if not is_mapped:
                raise HTTPException(status_code=403, detail="You don't have permission to access this member's sessions")
        
        # Fetch sessions for the requested member_id
        sessions = await crud.get_sessions_by_user(db, member_id)
        if not sessions:
            logger.info(f"No sessions found for member ID: {member_id}")
            return []
        
        result = []
        for session in sessions:
            sets = await crud.get_sets_by_session(db, session.session_id)
            result.append(schemas.SessionWithSets(
                session_id=session.session_id,
                workout_date=session.workout_date,
                user_id=session.user_id,
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