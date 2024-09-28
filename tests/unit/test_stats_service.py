import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from backend.stats_service.main import app as stats_app
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_get_weekly_progress():
    # Mock User Service response
    mock_user_response = {
        "workout_frequency": 3
    }

    # Mock Workout Service response
    mock_workout_response = [
        {"workout_date": (datetime.now() - timedelta(days=1)).isoformat()},
        {"workout_date": (datetime.now() - timedelta(days=2)).isoformat()},
        {"workout_date": (datetime.now() - timedelta(days=8)).isoformat()},
    ]

    # Patch the httpx.AsyncClient.get method
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = [
            AsyncMock(status_code=200, json=lambda: mock_user_response),
            AsyncMock(status_code=200, json=lambda: mock_workout_response)
        ]

        async with AsyncClient(app=stats_app, base_url="http://test") as ac:
            response = await ac.get("/api/stats/weekly-progress/user1")

    assert response.status_code == 200
    data = response.json()
    assert "weeks" in data
    assert "counts" in data
    assert "goal" in data
    assert len(data["weeks"]) == 4
    assert len(data["counts"]) == 4
    assert data["goal"] == 3
    assert data["counts"][0] == 2  # Two workouts in the most recent week
    assert data["counts"][1] == 1  # One workout in the second most recent week

@pytest.mark.asyncio
async def test_get_weekly_progress_error_handling():
    # Mock User Service to raise an exception
    with patch("httpx.AsyncClient.get", side_effect=Exception("Mocked error")):
        async with AsyncClient(app=stats_app, base_url="http://test") as ac:
            response = await ac.get("/api/stats/weekly-progress/user1")

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
