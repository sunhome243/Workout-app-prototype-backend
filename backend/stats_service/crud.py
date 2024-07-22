import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

WORKOUT_SERVICE_URL = "http://localhost:8001"

def get_monday(date: datetime) -> datetime:
    return date - timedelta(days=date.weekday())

async def get_weekly_session_counts(user_id: str, end_date: datetime, token: str) -> List[Dict[str, Any]]:
    start_date = get_monday(end_date - timedelta(weeks=3))
    logger.info(f"Fetching session counts for user {user_id} from {start_date} to {end_date}")
    
    async with httpx.AsyncClient() as client:
        try:
            headers = {"Authorization": token}
            url = f"{WORKOUT_SERVICE_URL}/api/session_counts/{user_id}"
            params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
            logger.info(f"Sending request to: {url} with params: {params}")
            
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            session_counts = response.json()
            logger.info(f"Received session counts: {session_counts}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred: {str(e)}")
            raise

    total_sessions = sum(session_counts.values())
    
    weekly_counts = [
        {"week": f"{i} week{'s' if i > 1 else ''}", "sessions": total_sessions if i == 0 else 0}
        for i in range(4)
    ]
    
    logger.info(f"Calculated weekly counts: {weekly_counts}")
    return weekly_counts