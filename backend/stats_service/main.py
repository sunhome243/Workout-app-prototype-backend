# stats_service/main.py

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import httpx
from datetime import datetime, timedelta
import logging
from . import schemas, crud, utils
from typing import Dict, Optional, List


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs
USER_SERVICE_URL = "http://localhost:8000"
WORKOUT_SERVICE_URL = "http://localhost:8001"

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Stats Service API",
        version="1.0.0",
        description="API for workout statistics",
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
async def openapi():
    return app.openapi()

@app.get("/api/stats/last-updated")
async def get_last_updated(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    try:
        current_user = await utils.get_current_user(authorization)
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        last_updated = await crud.get_last_session_update(current_user['id'])
        
        return {"last_updated": last_updated}
    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.get("/api/stats/weekly-progress", response_model=schemas.WeeklyProgressResponse)
async def get_weekly_progress(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    
    try:
        current_user = await utils.get_current_user(authorization)
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Get user's workout goal
        user_data = await utils.get_member_me(authorization)
        workout_goal = user_data.get("workout_goal")
        logger.info(f"User data: {user_data}")
        logger.info(f"Workout goal: {workout_goal}")
        
        if workout_goal is None:
            logger.warning(f"Workout goal not found for user. Setting default value.")
            workout_goal = 0  # 기본값 설정
        
        # Get session counts for the last 4 weeks
        end_date = datetime.now()
        weekly_counts = await crud.get_weekly_session_counts(current_user['id'], end_date, authorization)

        return schemas.WeeklyProgressResponse(
            weeks=[count["week"] for count in weekly_counts],
            counts=[count["sessions"] for count in weekly_counts],
            goal=workout_goal
        )
    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")