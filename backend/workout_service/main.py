from fastapi import FastAPI, Depends, HTTPException, Request, Header
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

async def check_trainer_user_mapping(trainer_id: int, user_id: int, token: str):
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": token}
        try:
            response = await client.get(f"{USER_SERVICE_URL}/check-trainer-user-mapping/{trainer_id}/{user_id}", headers=headers)
            response.raise_for_status()
            result = await response.json()
            logger.debug(f"Trainer-user mapping check result: {result}")
            return result.get("exists", False)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred while checking trainer-user mapping: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Error checking trainer-user mapping: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error occurred while checking trainer-user mapping: {str(e)}")
            raise HTTPException(status_code=500, detail="Unexpected error occurred")

@app.post("/create_session", response_model=schemas.SessionIDMap)
async def create_session(
    request: Request,
    session_type_id: int,
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    logger.debug(f"Received request headers for create_session: {request.headers}")
    logger.debug(f"Attempting to authenticate with token: {authorization[:10]}...") # Log first 10 characters for security
    
    # Print token contents for debugging
    utils.print_token_contents(authorization)
    
    try:
        current_user = await utils.get_current_member(authorization)
        logger.debug(f"Authentication successful. Current user: {current_user}")
    except HTTPException as e:
        logger.error(f"Authentication error: {e.detail}")
        raise e

    try:
        user_id = current_user['id']
        is_pt = "Y" if current_user['user_type'] == 'trainer' else "N"
        
        session_data = {
            "workout_date": datetime.now().strftime("%Y-%m-%d"),
            "user_id": user_id,
            "trainer_id": user_id if current_user['user_type'] == 'trainer' else None,
            "is_pt": is_pt,
            "session_type_id": session_type_id
        }
        
        logger.debug(f"Attempting to create session with data: {session_data}")
        new_session = await crud.create_session(db, session_data)
        logger.info(f"Session created successfully: {new_session.session_id}")
        return new_session
    except ValueError as ve:
        logger.error(f"Validation error in create_session: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating session")
    
