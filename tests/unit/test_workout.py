import pytest
from unittest.mock import patch, AsyncMock, MagicMock, ANY
from datetime import date, datetime
from backend.workout_service import crud, utils, schemas
from fastapi import HTTPException
from types import SimpleNamespace

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.create_session")
async def test_create_session_user(mock_create_session, mock_get_current_member, workout_client):
    mock_current_user = {
        "id": "user1",
        "user_type": "user"
    }
    mock_get_current_member.return_value = mock_current_user
    mock_create_session.return_value = AsyncMock()
    mock_create_session.return_value.session_id = 1
    mock_create_session.return_value.session_type_id = 2
    mock_create_session.return_value.workout_date = date(2024, 7, 10)
    mock_create_session.return_value.user_id = "user1"
    mock_create_session.return_value.trainer_id = None
    mock_create_session.return_value.is_pt = "N"
    
    response = await workout_client.post("/api/create_session?session_type_id=2", headers={"Authorization": "Bearer mock_token"})
    
    assert response.status_code == 200
    assert response.json() == {
        "session_id": 1,
        "session_type_id": 2,
        "workout_date": "2024-07-10",
        "user_id": "user1",
        "trainer_id": None,
        "is_pt": "N"
    }

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.create_session")
@patch("backend.workout_service.crud.check_trainer_user_mapping")
async def test_create_session_trainer(mock_check_mapping, mock_create_session, mock_get_current_member, workout_client):
    mock_current_trainer = {
        "id": "trainer1",
        "user_type": "trainer"
    }
    mock_get_current_member.return_value = mock_current_trainer
    mock_create_session.return_value = AsyncMock()
    mock_create_session.return_value.session_id = 1
    mock_create_session.return_value.session_type_id = 3
    mock_create_session.return_value.workout_date = date(2024, 7, 10)
    mock_create_session.return_value.user_id = "user1"
    mock_create_session.return_value.trainer_id = "trainer1"
    mock_create_session.return_value.is_pt = "Y"

    mock_check_mapping.return_value = True

    response = await workout_client.post("/api/create_session?session_type_id=3&user_id=user1", headers={"Authorization": "Bearer mock_token"})
    
    assert response.status_code == 200
    assert response.json() == {
        "session_id": 1,
        "session_type_id": 3,
        "workout_date": "2024-07-10",
        "user_id": "user1",
        "trainer_id": "trainer1",
        "is_pt": "Y"
    }

@pytest.mark.asyncio
async def test_create_session_no_auth(workout_client):
    response = await workout_client.post("/api/create_session?session_type_id=2")
    assert response.status_code == 401
    assert response.json() == {"detail": "Authorization header is missing"}

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.record_set")
async def test_record_set(mock_record_set, mock_get_current_member, workout_client):
    mock_current_user = {
        "id": "user1",
        "user_type": "user"
    }
    mock_get_current_member.return_value = mock_current_user
    mock_record_set.return_value = AsyncMock()
    mock_record_set.return_value.session_id = 1
    mock_record_set.return_value.workout_key = 1
    mock_record_set.return_value.set_num = 1
    mock_record_set.return_value.weight = 50.0
    mock_record_set.return_value.reps = 10
    mock_record_set.return_value.rest_time = 60

    response = await workout_client.post(
        "/api/record_set?session_id=1&workout_key=1&set_num=1&weight=50.0&reps=10&rest_time=60",
        headers={"Authorization": "Bearer mock_token"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "session_id": 1,
        "workout_key": 1,
        "set_num": 1,
        "weight": 50.0,
        "reps": 10,
        "rest_time": 60
    }

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.get_sessions_by_user")
@patch("backend.workout_service.crud.get_sets_by_session")
@patch("backend.workout_service.crud.check_trainer_user_mapping")
async def test_get_sessions(mock_check_mapping, mock_get_sets, mock_get_sessions, mock_get_current_member, workout_client):
    mock_current_user = {
        "id": "user1",
        "user_type": "user"
    }
    mock_get_current_member.return_value = mock_current_user
    mock_get_sessions.return_value = [
        AsyncMock(session_id=1, workout_date=date(2024, 7, 10), user_id="user1", trainer_id=None, is_pt="N", session_type_id=2)
    ]
    mock_get_sets.return_value = [
        AsyncMock(session_id=1, workout_key=1, set_num=1, weight=50.0, reps=10, rest_time=60)
    ]
    mock_check_mapping.return_value = True

    response = await workout_client.get("/api/get_sessions/user1", headers={"Authorization": "Bearer mock_token"})

    assert response.status_code == 200
    assert response.json() == [{
        "session_id": 1,
        "workout_date": "2024-07-10",
        "user_id": "user1",
        "trainer_id": None,
        "is_pt": "N",
        "session_type_id": 2,
        "sets": [{
            "session_id": 1,
            "workout_key": 1,
            "set_num": 1,
            "weight": 50.0,
            "reps": 10,
            "rest_time": 60
        }]
    }]


@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.create_quest")
@patch("backend.workout_service.crud.check_trainer_user_mapping")
async def test_create_quest(mock_check_mapping, mock_create_quest, mock_get_current_member, workout_client):
    # Setup mock trainer
    mock_current_trainer = {
        "id": "trainer1",
        "user_type": "trainer"
    }
    mock_get_current_member.return_value = mock_current_trainer
    mock_check_mapping.return_value = True

    # Setup mock quest response
    mock_quest = {
        "quest_id": 1,
        "trainer_id": "trainer1",
        "user_id": "user1",
        "status": False,
        "created_at": datetime(2024, 7, 10, 12, 0, 0),
        "workouts": [
            {
                "quest_id": 1,
                "workout_key": 1,
                "sets": [
                    {
                        "quest_id": 1,
                        "workout_key": 1,
                        "set_number": 1,
                        "weight": 50.0,
                        "reps": 10,
                        "rest_time": 60
                    }
                ]
            }
        ]
    }

    mock_create_quest.return_value = mock_quest

    # Prepare quest data
    quest_data = {
        "user_id": "user1",
        "workouts": [
            {
                "workout_key": 1,
                "sets": [
                    {
                        "set_number": 1,
                        "weight": 50.0,
                        "reps": 10,
                        "rest_time": 60
                    }
                ]
            }
        ]
    }

    # Send request
    response = await workout_client.post("/api/create_quest", json=quest_data, headers={"Authorization": "Bearer mock_token"})

    # Assert response
    assert response.status_code == 200
    assert response.json() == {
        "quest_id": 1,
        "trainer_id": "trainer1",
        "user_id": "user1",
        "status": False,
        "created_at": "2024-07-10T12:00:00",
        "workouts": [
            {
                "quest_id": 1,
                "workout_key": 1,
                "sets": [
                    {
                        "quest_id": 1,
                        "workout_key": 1,
                        "set_number": 1,
                        "weight": 50.0,
                        "reps": 10,
                        "rest_time": 60
                    }
                ]
            }
        ]
    }

    # Verify function calls
    mock_get_current_member.assert_called_once()
    mock_check_mapping.assert_called_once_with("trainer1", "user1", "Bearer mock_token")
    mock_create_quest.assert_called_once()

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.get_quests_by_trainer")
async def test_read_quests_trainer(mock_get_quests, mock_get_current_member, workout_client):
    mock_current_trainer = {
        "id": "trainer1",
        "user_type": "trainer"
    }
    mock_get_current_member.return_value = mock_current_trainer
    mock_get_quests.return_value = [
        AsyncMock(
            quest_id=1,
            trainer_id="trainer1",
            user_id="user1",
            status=False,
            created_at=datetime(2024, 7, 10, 12, 0, 0),
            workouts=[
                AsyncMock(
                    quest_id=1,
                    workout_key=1,
                    sets=[
                        AsyncMock(
                            quest_id=1,
                            workout_key=1,
                            set_number=1,
                            weight=50.0,
                            reps=10,
                            rest_time=60
                        )
                    ]
                )
            ]
        )
    ]

    response = await workout_client.get("/api/quests", headers={"Authorization": "Bearer mock_token"})

    assert response.status_code == 200
    assert response.json() == [{
        "quest_id": 1,
        "trainer_id": "trainer1",
        "user_id": "user1",
        "status": False,
        "created_at": "2024-07-10T12:00:00",
        "workouts": [
            {
                "quest_id": 1,
                "workout_key": 1,
                "sets": [
                    {
                        "quest_id": 1,
                        "workout_key": 1,
                        "set_number": 1,
                        "weight": 50.0,
                        "reps": 10,
                        "rest_time": 60
                    }
                ]
            }
        ]
    }]

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.get_quests_by_trainer_and_user")
@patch("backend.workout_service.crud.check_trainer_user_mapping")
async def test_read_quests_for_user(mock_check_mapping, mock_get_quests, mock_get_current_member, workout_client):
    mock_current_trainer = {
        "id": "trainer1",
        "user_type": "trainer"
    }
    mock_get_current_member.return_value = mock_current_trainer
    mock_check_mapping.return_value = True
    mock_get_quests.return_value = [
        AsyncMock(
            quest_id=1,
            trainer_id="trainer1",
            user_id="user1",
            status=False,
            created_at=datetime(2024, 7, 10, 12, 0, 0),
            workouts=[
                AsyncMock(
                    quest_id=1,
                    workout_key=1,
                    sets=[
                        AsyncMock(
                            quest_id=1,
                            workout_key=1,
                            set_number=1,
                            weight=50.0,
                            reps=10,
                            rest_time=60
                        )
                    ]
                )
            ]
        )
    ]

    response = await workout_client.get("/api/quests/user1", headers={"Authorization": "Bearer mock_token"})

    assert response.status_code == 200
    assert response.json() == [{
        "quest_id": 1,
        "trainer_id": "trainer1",
        "user_id": "user1",
        "status": False,
        "created_at": "2024-07-10T12:00:00",
        "workouts": [
            {
                "quest_id": 1,
                "workout_key": 1,
                "sets": [
                    {
                        "quest_id": 1,
                        "workout_key": 1,
                        "set_number": 1,
                        "weight": 50.0,
                        "reps": 10,
                        "rest_time": 60
                    }
                ]
            }
        ]
    }]
    
@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.get_quest_by_id")
@patch("backend.workout_service.crud.update_quest_status")
async def test_update_quest_status(mock_update_status, mock_get_quest, mock_get_current_member, workout_client):
    mock_current_user = {
        "id": "user1",
        "user_type": "user"
    }
    mock_get_current_member.return_value = mock_current_user

    mock_quest = MagicMock()
    mock_quest.quest_id = 1
    mock_quest.trainer_id = "trainer1"
    mock_quest.user_id = "user1"
    mock_quest.status = False
    mock_quest.created_at = datetime(2024, 7, 10, 12, 0, 0)
    mock_quest.workouts = [MagicMock()]
    mock_quest.workouts[0].quest_id = 1
    mock_quest.workouts[0].workout_key = 1
    mock_quest.workouts[0].sets = [MagicMock()]
    mock_quest.workouts[0].sets[0].quest_id = 1
    mock_quest.workouts[0].sets[0].workout_key = 1
    mock_quest.workouts[0].sets[0].set_number = 1
    mock_quest.workouts[0].sets[0].weight = 50.0
    mock_quest.workouts[0].sets[0].reps = 10
    mock_quest.workouts[0].sets[0].rest_time = 60

    mock_get_quest.return_value = mock_quest
    mock_update_status.return_value = mock_quest
    mock_update_status.return_value.status = True

    response = await workout_client.patch("/api/quests/1/status?status=true", headers={"Authorization": "Bearer mock_token"})

    assert response.status_code == 200
    assert response.json()["status"] == True

    mock_get_current_member.assert_called_once()
    mock_get_quest.assert_called_once_with(ANY, 1)
    mock_update_status.assert_called_once_with(ANY, 1, True)


@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.get_quest_by_id")
@patch("backend.workout_service.crud.delete_quest")
async def test_delete_quest(mock_delete_quest, mock_get_quest, mock_get_current_member, workout_client):
    mock_current_trainer = {
        "id": "trainer1",
        "user_type": "trainer"
    }
    mock_get_current_member.return_value = mock_current_trainer
    mock_get_quest.return_value = AsyncMock(
        quest_id=1,
        trainer_id="trainer1",
        user_id="user1",
        status=False
    )
    mock_delete_quest.return_value = True

    response = await workout_client.delete("/api/quests/1", headers={"Authorization": "Bearer mock_token"})

    assert response.status_code == 204

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.get_workout_records")
async def test_get_workout_records(mock_get_records, mock_get_current_member, workout_client):
    mock_current_user = {
        "id": "user1",
        "user_type": "user"
    }
    mock_get_current_member.return_value = mock_current_user
    mock_get_records.return_value = {
        1: {
            "date": datetime(2024, 7, 10, 12, 0, 0),
            "sets": [
                {
                    "set_number": 1,
                    "weight": 50.0,
                    "reps": 10,
                    "rest_time": 60
                }
            ]
        }
    }

    response = await workout_client.get("/api/workout-records/1", headers={"Authorization": "Bearer mock_token"})

    assert response.status_code == 200
    assert response.json() == {
        "1": {
            "date": "2024-07-10T12:00:00",
            "sets": [
                {
                    "set_number": 1,
                    "weight": 50.0,
                    "reps": 10,
                    "rest_time": 60
                }
            ]
        }
    }

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.get_workout_name")
async def test_get_workout_name(mock_get_workout_name, mock_get_current_member, workout_client):
    mock_current_user = {
        "id": "user1",
        "user_type": "user"
    }
    mock_get_current_member.return_value = mock_current_user
    mock_get_workout_name.return_value = "Bench Press"

    response = await workout_client.get("/api/workout-name/1", headers={"Authorization": "Bearer mock_token"})

    assert response.status_code == 200
    assert response.json() == {
        "workout_key": 1,
        "workout_name": "Bench Press"
    }

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.get_workouts_by_part")
async def test_get_workouts_by_part(mock_get_workouts_by_part, mock_get_current_member, workout_client):
    mock_current_user = {
        "id": "user1",
        "user_type": "user"
    }
    mock_get_current_member.return_value = mock_current_user
    mock_get_workouts_by_part.return_value = {
        "Chest": [
            {
                "workout_key": 1,
                "workout_name": "Bench Press"
            },
            {
                "workout_key": 2,
                "workout_name": "Incline Press"
            }
        ],
        "Back": [
            {
                "workout_key": 3,
                "workout_name": "Pull-ups"
            }
        ]
    }

    response = await workout_client.get("/api/workouts-by-part", headers={"Authorization": "Bearer mock_token"})

    assert response.status_code == 200
    assert response.json() == {
        "Chest": [
            {
                "workout_key": 1,
                "workout_name": "Bench Press"
            },
            {
                "workout_key": 2,
                "workout_name": "Incline Press"
            }
        ],
        "Back": [
            {
                "workout_key": 3,
                "workout_name": "Pull-ups"
            }
        ]
    }

# 추가적인 엣지 케이스 테스트

@pytest.mark.asyncio
async def test_create_session_invalid_session_type(workout_client):
    response = await workout_client.post("/api/create_session", headers={"Authorization": "Bearer mock_token"})
    assert response.status_code == 422

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.get_quest_by_id")
async def test_update_quest_status_unauthorized(mock_get_quest, mock_get_current_member, workout_client):
    mock_current_user = {
        "id": "user2",
        "user_type": "user"
    }
    mock_get_current_member.return_value = mock_current_user

    mock_quest = MagicMock()
    mock_quest.user_id = "user1"
    mock_get_quest.return_value = mock_quest

    response = await workout_client.patch("/api/quests/1/status?status=true", headers={"Authorization": "Bearer mock_token"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to update this quest"}


@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_member")
@patch("backend.workout_service.crud.get_quest_by_id")
async def test_delete_quest_unauthorized(mock_get_quest, mock_get_current_member, workout_client):
    mock_get_current_member.return_value = {"id": "user1", "user_type": "user"}
    mock_get_quest.return_value = AsyncMock(trainer_id="trainer1")
    response = await workout_client.delete("/api/quests/1", headers={"Authorization": "Bearer mock_token"})
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_get_workout_name_not_found(workout_client, mock_auth):
    with patch("backend.workout_service.crud.get_workout_name", return_value=None):
        response = await workout_client.get("/api/workout-name/9999", headers={"Authorization": "Bearer mock_token"})
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_workouts_by_part_with_filter(workout_client, mock_auth):
    with patch("backend.workout_service.crud.get_workouts_by_part", return_value={}):
        response = await workout_client.get("/api/workouts-by-part?workout_part_id=1", headers={"Authorization": "Bearer mock_token"})
    assert response.status_code == 200