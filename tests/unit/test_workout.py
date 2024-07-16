import pytest
from unittest.mock import patch, AsyncMock
from datetime import date
from backend.workout_service import crud, utils

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.create_session")
async def test_create_session_user(mock_create_session, mock_get_current_member, workout_client):
    mock_current_user = {
        "id": 1,
        "user_type": "user"
    }
    mock_get_current_member.return_value = mock_current_user
    mock_create_session.return_value = AsyncMock()
    mock_create_session.return_value.session_id = 1
    mock_create_session.return_value.session_type_id = 2
    mock_create_session.return_value.workout_date = date(2024, 7, 10)
    mock_create_session.return_value.user_id = "AAAAA"
    mock_create_session.return_value.trainer_id = None
    mock_create_session.return_value.is_pt = "N"
    
    response = await workout_client.post("/create_session?session_type_id=2", headers={"Authorization": "Bearer mock_token"})
    
    assert response.status_code == 200
    assert response.json() == {
        "session_id": 1,
        "session_type_id": 2,
        "workout_date": "2024-07-10",
        "user_id": "AAAAA",
        "trainer_id": None,
        "is_pt": "N"
    }

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.create_session")
@patch("backend.workout_service.main.check_trainer_user_mapping")
async def test_create_session_trainer(mock_check_mapping, mock_create_session, mock_get_current_member, workout_client):
    mock_current_trainer = {
        "id": 1,
        "user_type": "trainer"
    }
    mock_get_current_member.return_value = mock_current_trainer
    mock_create_session.return_value = AsyncMock()
    mock_create_session.return_value.session_id = 1
    mock_create_session.return_value.session_type_id = 3
    mock_create_session.return_value.workout_date = date(2024, 7, 10)
    mock_create_session.return_value.user_id = "AAAAA"
    mock_create_session.return_value.trainer_id = "AAAAA"
    mock_create_session.return_value.is_pt = "Y"

    mock_check_mapping.return_value = True

    response = await workout_client.post("/create_session?session_type_id=3&user_id=2", headers={"Authorization": "Bearer mock_token"})
    
    assert response.status_code == 200
    assert response.json() == {
        "session_id": 1,
        "session_type_id": 3,
        "workout_date": "2024-07-10",
        "user_id": "AAAAA",
        "trainer_id": "AAAAA",
        "is_pt": "Y"
    }


@pytest.mark.asyncio
async def test_create_session_no_auth(workout_client):
    response = await workout_client.post("/create_session?session_type_id=2")
    assert response.status_code == 401
    assert response.json() == {"detail": "Authorization header is missing"}

# New test for invalid session_type_id
@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
async def test_create_session_invalid_session_type(mock_get_current_member, workout_client):
    mock_current_user = {
        "id": 1,
        "user_type": "user"
    }
    mock_get_current_member.return_value = mock_current_user

    response = await workout_client.post("/create_session", headers={"Authorization": "Bearer mock_token"})
    
    assert response.status_code == 422  # Unprocessable Entity
    assert "session_type_id" in response.json()["detail"][0]["loc"]