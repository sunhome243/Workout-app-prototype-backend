import pytest
from unittest.mock import patch, AsyncMock, MagicMock, ANY
from datetime import date, datetime
from backend.workout_service import crud, utils, schemas
from fastapi import HTTPException
from types import SimpleNamespace
    
@pytest.mark.asyncio
async def test_create_session_no_auth(workout_client):
    response = await workout_client.post("/api/create_session?session_type_id=2")
    assert response.status_code == 401
    assert response.json() == {"detail": "Authorization header is missing"}


@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_user")
@patch("backend.workout_service.crud.get_sessions_by_member")
@patch("backend.workout_service.crud.get_sets_by_session")
@patch("backend.workout_service.crud.check_trainer_member_mapping")
async def test_get_sessions(mock_check_mapping, mock_get_sets, mock_get_sessions, mock_get_current_user, workout_client):
    mock_current_member = {
        "id": "member1",
        "user_type": "member"
    }
    mock_get_current_user.return_value = mock_current_member
    mock_get_sessions.return_value = [
        AsyncMock(session_id=1, workout_date=date(2024, 7, 10), member_uid="member1", trainer_uid=None, is_pt=False, session_type_id=2)
    ]
    mock_get_sets.return_value = [
        AsyncMock(session_id=1, workout_key=1, set_num=1, weight=50.0, reps=10, rest_time=60)
    ]
    mock_check_mapping.return_value = True

    response = await workout_client.get("/api/get_sessions/member1", headers={"Authorization": "Bearer mock_token"})

    assert response.status_code == 200
    assert response.json() == [{
        "session_id": 1,
        "member_uid": "member1",
        "trainer_uid": None,
        "is_pt": False,
        "session_type_id": 2,
        "sets": [{
            "session_id": 1,
            "workout_key": 1,
            "set_num": 1,
            "weight": 50.0,
            "reps": 10,
            "rest_time": 60
        }],
    }]


@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_user")
@patch("backend.workout_service.crud.create_quest")
@patch("backend.workout_service.crud.check_trainer_member_mapping")
async def test_create_quest(mock_check_mapping, mock_create_quest, mock_get_current_user, workout_client):
    # Setup mock trainer
    mock_current_trainer = {
        "id": "trainer1",
        "user_type": "trainer"
    }
    mock_get_current_user.return_value = mock_current_trainer
    mock_check_mapping.return_value = True

    # Setup mock quest response
    mock_quest = {
        "quest_id": 1,
        "trainer_uid": "trainer1",
        "member_uid": "member1",
        "status": schemas.QuestStatus.NOT_STARTED,
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
        "member_uid": "member1",
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
        "trainer_uid": "trainer1",
        "member_uid": "member1",
        "status": "Not started",
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
    mock_get_current_user.assert_called_once()
    mock_check_mapping.assert_called_once_with("trainer1", "member1", "Bearer mock_token")
    mock_create_quest.assert_called_once()

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_user")
@patch("backend.workout_service.crud.get_quests_by_trainer")
async def test_read_quests_trainer(mock_get_quests, mock_get_current_user, workout_client):
    mock_current_trainer = {
        "id": "trainer1",
        "user_type": "trainer"
    }
    mock_get_current_user.return_value = mock_current_trainer
    mock_get_quests.return_value = [
        AsyncMock(
            quest_id=1,
            trainer_uid="trainer1",
            member_uid="member1",
            status= schemas.QuestStatus.NOT_STARTED,
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
        "trainer_uid": "trainer1",
        "member_uid": "member1",
        "status": schemas.QuestStatus.NOT_STARTED,
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
@patch("backend.workout_service.utils.get_current_user")
@patch("backend.workout_service.crud.get_quests_by_trainer_and_member")
@patch("backend.workout_service.crud.check_trainer_member_mapping")
async def test_read_quests_for_member(mock_check_mapping, mock_get_quests, mock_get_current_user, workout_client):
    mock_current_trainer = {
        "id": "trainer1",
        "user_type": "trainer"
    }
    mock_get_current_user.return_value = mock_current_trainer
    mock_check_mapping.return_value = True
    mock_get_quests.return_value = [
        AsyncMock(
            quest_id=1,
            trainer_uid="trainer1",
            member_uid="member1",
            status= schemas.QuestStatus.NOT_STARTED,
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

    response = await workout_client.get("/api/quests/member1", headers={"Authorization": "Bearer mock_token"})

    assert response.status_code == 200
    assert response.json() == [{
        "quest_id": 1,
        "trainer_uid": "trainer1",
        "member_uid": "member1",
        "status": schemas.QuestStatus.NOT_STARTED.value,
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
@patch("backend.workout_service.utils.get_current_user")
@patch("backend.workout_service.crud.get_quest_by_id")
@patch("backend.workout_service.crud.delete_quest")
async def test_delete_quest(mock_delete_quest, mock_get_quest, mock_get_current_user, workout_client):
    mock_current_trainer = {
        "id": "trainer1",
        "user_type": "trainer"
    }
    mock_get_current_user.return_value = mock_current_trainer
    mock_get_quest.return_value = AsyncMock(
        quest_id=1,
        trainer_uid="trainer1",
        member_uid="member1",
        status=False
    )
    mock_delete_quest.return_value = True

    response = await workout_client.delete("/api/quests/1", headers={"Authorization": "Bearer mock_token"})

    assert response.status_code == 204

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_user")
@patch("backend.workout_service.crud.get_workout_records")
async def test_get_workout_records(mock_get_records, mock_get_current_user, workout_client):
    mock_current_member = {
        "id": "member1",
        "user_type": "member"
    }
    mock_get_current_user.return_value = mock_current_member
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
@patch("backend.workout_service.utils.get_current_user")
@patch("backend.workout_service.crud.get_workout_name")
async def test_get_workout_name(mock_get_workout_name, mock_get_current_user, workout_client):
    mock_current_member = {
        "id": "member1",
        "user_type": "member"
    }
    mock_get_current_user.return_value = mock_current_member
    mock_get_workout_name.return_value = "Bench Press"

    response = await workout_client.get("/api/workout-name/1", headers={"Authorization": "Bearer mock_token"})

    assert response.status_code == 200
    assert response.json() == {
        "workout_key": 1,
        "workout_name": "Bench Press"
    }

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_user")
@patch("backend.workout_service.crud.get_workouts_by_part")
async def test_get_workouts_by_part(mock_get_workouts_by_part, mock_get_current_user, workout_client):
    mock_current_member = {
        "id": "member1",
        "user_type": "member"
    }
    mock_get_current_user.return_value = mock_current_member
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

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_user")
@patch("backend.workout_service.crud.create_session")
async def test_create_session_member(mock_create_session, mock_get_current_user, workout_client):
    mock_current_member = {
        "id": "member1",
        "user_type": "member"
    }
    mock_get_current_user.return_value = mock_current_member
    mock_create_session.return_value = AsyncMock()
    mock_create_session.return_value.session_id = 1
    mock_create_session.return_value.session_type_id = 2
    mock_create_session.return_value.workout_date = date(2024, 7, 10)
    mock_create_session.return_value.member_uid = "member1"
    mock_create_session.return_value.trainer_uid = None
    mock_create_session.return_value.is_pt = False
    mock_create_session.return_value.quest_id = 1
    
    response = await workout_client.post("/api/create_session?session_type_id=2&quest_id=1", headers={"Authorization": "Bearer mock_token"})
    
    assert response.status_code == 200
    assert response.json() == {
        "session_id": 1,
        "session_type_id": 2,
        "workout_date": "2024-07-10",
        "member_uid": "member1",
        "trainer_uid": None,
        "is_pt": False,
        "quest_id": 1,
        'workout_date': '2024-07-10T00:00:00'
    }

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_user")
@patch("backend.workout_service.crud.create_session")
@patch("backend.workout_service.crud.check_trainer_member_mapping")
async def test_create_session_trainer(mock_check_mapping, mock_create_session, mock_get_current_user, workout_client):
    mock_current_trainer = {
        "id": "trainer1",
        "user_type": "trainer"
    }
    mock_get_current_user.return_value = mock_current_trainer
    mock_create_session.return_value = AsyncMock()
    mock_create_session.return_value.session_id = 1
    mock_create_session.return_value.session_type_id = 3
    mock_create_session.return_value.workout_date = date(2024, 7, 10)
    mock_create_session.return_value.member_uid = "member1"
    mock_create_session.return_value.trainer_uid = "trainer1"
    mock_create_session.return_value.is_pt = True
    mock_create_session.return_value.quest_id = None
    mock_check_mapping.return_value = True

    # Remove session_type_id from the request
    response = await workout_client.post("/api/create_session?member_uid=member1", headers={"Authorization": "Bearer mock_token"})
    
    assert response.status_code == 200
    assert response.json() == {
        "session_id": 1,
        "session_type_id": 3,
        "workout_date": "2024-07-10T00:00:00",
        "member_uid": "member1",
        "trainer_uid": "trainer1",
        "is_pt": True,
        "quest_id": None
    }

    # Verify that create_session was called with the correct arguments
    mock_create_session.assert_called_once_with(
        ANY,  # db
        None,  # session_type_id should be None in the request
        None,  # quest_id
        "member1",  # member_uid
        mock_current_trainer,
        "Bearer mock_token"
    )

@pytest.mark.asyncio
async def test_create_session_no_auth(workout_client):
    response = await workout_client.post("/api/create_session?session_type_id=2")
    assert response.status_code == 401
    assert response.json() == {"detail": "Authorization header is missing"}

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_user")
@patch("backend.workout_service.crud.get_oldest_not_started_quest")
async def test_get_oldest_not_started_quest(mock_get_quest, mock_get_current_user, workout_client):
    mock_current_member = {
        "id": "member1",
        "user_type": "member"
    }
    mock_get_current_user.return_value = mock_current_member

    # Create two quests with different dates
    older_quest = AsyncMock(
        quest_id=1,
        trainer_uid="trainer1",
        member_uid="member1",
        status=schemas.QuestStatus.NOT_STARTED,
        created_at=datetime(2024, 7, 1, 12, 0, 0),
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

    newer_quest = AsyncMock(
        quest_id=2,
        trainer_uid="trainer1",
        member_uid="member1",
        status=schemas.QuestStatus.NOT_STARTED,
        created_at=datetime(2024, 7, 10, 12, 0, 0),
        workouts=[
            AsyncMock(
                quest_id=2,
                workout_key=2,
                sets=[
                    AsyncMock(
                        quest_id=2,
                        workout_key=2,
                        set_number=1,
                        weight=60.0,
                        reps=8,
                        rest_time=90
                    )
                ]
            )
        ]
    )

    # Mock the get_oldest_not_started_quest function to return the older quest
    mock_get_quest.return_value = older_quest

    response = await workout_client.get("/api/get_oldest_not_started_quest", headers={"Authorization": "Bearer mock_token"})

    assert response.status_code == 200
    quest_data = response.json()
    
    assert quest_data["quest_id"] == 1
    assert quest_data["created_at"] == "2024-07-01T12:00:00"
    assert quest_data["status"] == "Not started"
    
    # Verify that the returned quest is indeed the older one
    assert quest_data["created_at"] < "2024-07-10T12:00:00"

    # Verify the complete structure of the returned quest
    assert quest_data == {
        "quest_id": 1,
        "trainer_uid": "trainer1",
        "member_uid": "member1",
        "status": "Not started",
        "created_at": "2024-07-01T12:00:00",
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

    # Verify that the get_oldest_not_started_quest function was called with the correct parameters
    mock_get_quest.assert_called_once_with(ANY, "member1")

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_user")
@patch("backend.workout_service.crud.save_session")
async def test_save_session(mock_save_session, mock_get_current_user, workout_client):
    mock_current_member = {
        "id": "member1",
        "user_type": "member"
    }
    mock_get_current_user.return_value = mock_current_member
    
    mock_save_session.return_value = AsyncMock(
        session_id=1,
        session_type_id=2,
        workout_date=date(2024, 7, 10),
        member_uid="member1",
        trainer_uid=None,
        is_pt=False,
        quest_id=1
    )

    session_data = {
        "session_id": 1,
        "exercises": [
            {
                "workout_key": 1,
                "sets": [
                    {
                        "set_num": 1,
                        "weight": 50.0,
                        "reps": 10,
                        "rest_time": 60
                    },
                    {
                        "set_num": 2,
                        "weight": 52.5,
                        "reps": 8,
                        "rest_time": 90
                    }
                ]
            },
            {
                "workout_key": 2,
                "sets": [
                    {
                        "set_num": 1,
                        "weight": 30.0,
                        "reps": 12,
                        "rest_time": 45
                    }
                ]
            }
        ]
    }

    response = await workout_client.post("/api/save_session", json=session_data, headers={"Authorization": "Bearer mock_token"})

    assert response.status_code == 200
    assert response.json() == {
        "session_id": 1,
        "session_type_id": 2,
        "workout_date": "2024-07-10T00:00:00",
        "member_uid": "member1",
        "trainer_uid": None,
        "is_pt": False,
        "quest_id": 1
    }

    # Verify that save_session was called with the correct arguments
    mock_save_session.assert_called_once()
    call_args = mock_save_session.call_args[0]
    assert call_args[1].session_id == 1
    assert len(call_args[1].exercises) == 2
    assert call_args[1].exercises[0].workout_key == 1
    assert len(call_args[1].exercises[0].sets) == 2
    assert call_args[1].exercises[1].workout_key == 2
    assert len(call_args[1].exercises[1].sets) == 1

# 추가적인 엣지 케이스 테스트

@pytest.mark.asyncio
@patch("backend.workout_service.utils.get_current_user")
@patch("backend.workout_service.crud.get_quest_by_id")
async def test_delete_quest_unauthorized(mock_get_quest, mock_get_current_user, workout_client):
    mock_get_current_user.return_value = {"id": "member1", "user_type": "member"}
    mock_get_quest.return_value = AsyncMock(trainer_uid="trainer1")
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