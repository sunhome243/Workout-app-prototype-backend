import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock
from backend.user_service import schemas, models, crud, utils

class TestTrainerRouter:
    @pytest.mark.asyncio
    async def test_create_trainer(self, user_client: AsyncClient, db_session, monkeypatch):
        mock_trainer = models.Trainer(
            trainer_id=1, 
            email="trainer@example.com", 
            first_name="John", 
            last_name="Doe",
            role="trainer",
            hashed_password="hashed_password"
        )
        mock_create_trainer = AsyncMock(return_value=mock_trainer)
        monkeypatch.setattr(crud, "create_trainer", mock_create_trainer)
        
        data = {"email": "trainer@example.com", "password": "password", "first_name": "John", "last_name": "Doe"}
        response = await user_client.post("/trainers/", json=data)
        assert response.status_code == 200
        assert response.json()["email"] == data["email"]
        assert response.json()["role"] == "trainer"
    
    @pytest.mark.asyncio
    async def test_login_trainer(self, user_client, db_session, monkeypatch):
        print(f"Type of user_client: {type(user_client)}")
        print(f"Attributes of user_client: {dir(user_client)}")
        
        mock_trainer = models.Trainer(
            trainer_id=1,
            email="trainer_test@example.com",
            first_name="Trainer",
            last_name="Test",
            role="trainer"
        )
        mock_authenticate = AsyncMock(return_value=(mock_trainer, "trainer"))
        mock_create_token = MagicMock(return_value="mocked_trainer_access_token")
        monkeypatch.setattr(utils, "authenticate_member", mock_authenticate)
        monkeypatch.setattr(utils, "create_access_token", mock_create_token)

        login_data = {"username": "trainer_test@example.com", "password": "trainerpassword"}
        response = await user_client.post("/login", data=login_data)

        assert response.status_code == 200
        response_json = response.json()
        assert "access_token" in response_json
        assert response_json["access_token"] == "mocked_trainer_access_token"
        assert response_json["token_type"] == "bearer"

        mock_authenticate.assert_awaited_once_with(db_session, "trainer_test@example.com", "trainerpassword")
        mock_create_token.assert_called_once()
        call_args = mock_create_token.call_args[1]
        assert call_args["data"] == {"sub": str(mock_trainer.trainer_id), "type": "trainer"}
        assert "expires_delta" in call_args

    @pytest.mark.asyncio
    async def test_update_trainer(self, authenticated_trainer_client: AsyncClient, db_session, monkeypatch):
        update_data = {"first_name": "Updated", "last_name": "Trainer"}
        mock_updated_trainer = models.Trainer(
            trainer_id=1,  
            **update_data,
            email="trainer@example.com",
            role="trainer",
            hashed_password="hashed_password"
        )
        mock_update_trainer = AsyncMock(return_value=mock_updated_trainer)
        monkeypatch.setattr(crud, "update_trainer", mock_update_trainer)

        response = await authenticated_trainer_client.patch("/trainers/me", json=update_data)
        assert response.status_code == 200
        assert response.json()["first_name"] == update_data["first_name"]
        assert response.json()["last_name"] == update_data["last_name"]

    @pytest.mark.asyncio
    async def test_read_specific_connected_user_info(self, authenticated_trainer_client: AsyncClient, db_session, monkeypatch):
        mock_user_info = schemas.ConnectedUserInfo(
            user_id=2,
            email="user@example.com",
            first_name="Test",
            last_name="User",
            age=30,
            height=180.5,
            weight=75.0,
            workout_duration=60,
            workout_frequency=3,
            workout_goal=1
        )
        
        mock_get_info = AsyncMock(return_value=mock_user_info)
        monkeypatch.setattr(crud, "get_specific_connected_user_info", mock_get_info)

        response = await authenticated_trainer_client.get("/trainer/connected-users/2")

        assert response.status_code == 200
        response_data = response.json()

        expected_fields = [
            "user_id", "first_name", "last_name", "age", "height", "weight",
            "workout_duration", "workout_frequency", "workout_goal"
        ]
        for field in expected_fields:
            assert field in response_data, f"Field '{field}' is missing in the response"
            assert response_data[field] == getattr(mock_user_info, field), f"Mismatch in field '{field}'"

        if "email" in response_data:
            assert response_data["email"] == mock_user_info.email
        else:
            print("Note: 'email' field is not present in the API response")
        
    @pytest.mark.asyncio
    async def test_check_trainer_user_mapping(self, authenticated_trainer_client: AsyncClient, db_session, monkeypatch):
        mock_mapping = AsyncMock()
        mock_mapping.status = models.MappingStatus.accepted
        mock_get_mapping = AsyncMock(return_value=mock_mapping)
        monkeypatch.setattr(crud, "get_trainer_user_mapping", mock_get_mapping)
        
        response = await authenticated_trainer_client.get("/check-trainer-user-mapping/1/2")
        
        assert response.status_code == 200
        assert response.json() == {"exists": True}

    @pytest.mark.asyncio
    async def test_update_trainer_user_mapping_status(self, authenticated_trainer_client: AsyncClient, db_session, monkeypatch):
        mock_db_mapping = AsyncMock()
        mock_db_mapping.id = 1
        mock_db_mapping.trainer_id = 1
        mock_db_mapping.user_id = 2
        mock_db_mapping.status = models.MappingStatus.accepted
        mock_update_mapping = AsyncMock(return_value=mock_db_mapping)
        monkeypatch.setattr(crud, "update_trainer_user_mapping_status", mock_update_mapping)
        
        status_data = {"new_status": "accepted"}
        response = await authenticated_trainer_client.put("/trainer-user-mapping/1/status", json=status_data)
        
        assert response.status_code == 200
        assert response.json() == {
            "id": 1,
            "trainer_id": 1,
            "user_id": 2,
            "status": "accepted"
        }