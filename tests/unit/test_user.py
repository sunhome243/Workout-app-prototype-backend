import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock
from backend.user_service import schemas, models, crud, utils
from datetime import datetime, timedelta

class TestUserRouter:
    @pytest.mark.asyncio
    async def test_create_user(self, user_client: AsyncClient, db_session, monkeypatch):
        mock_user = models.User(
            user_id="AAAAA", 
            email="test@example.com", 
            first_name="Sunho", 
            last_name="Kim",
            role="user"
        )
        mock_create_user = AsyncMock(return_value=mock_user)
        monkeypatch.setattr(crud, "create_user", mock_create_user)
        
        data = {"user_id": "AAAAA", "email": "test@example.com", "password": "password", "first_name": "Sunho", "last_name": "Kim"}
        response = await user_client.post("/api/users/", json=data)
        assert response.status_code == 200
        assert response.json()["email"] == data["email"]
        assert response.json()["email"] == data["email"]
    
    @pytest.mark.asyncio
    async def test_login_user(self, user_client, db_session, monkeypatch):
        print(f"Type of user_client: {type(user_client)}")
        print(f"Attributes of user_client: {dir(user_client)}")
        mock_user = models.User(
            user_id="AAAAA",
            email="login_test@example.com",
            first_name="Login",
            last_name="Test",
            role="user"
        )
        mock_authenticate = AsyncMock(return_value=(mock_user, "user"))
        mock_create_token = MagicMock(return_value="mocked_access_token")
        monkeypatch.setattr(utils, "authenticate_member", mock_authenticate)
        monkeypatch.setattr(utils, "create_access_token", mock_create_token)

        login_data = {"username": "login_test@example.com", "password": "password"}
        response = await user_client.post("/api/login", data=login_data)

        assert response.status_code == 200
        response_json = response.json()
        assert "access_token" in response_json
        assert response_json["access_token"] == "mocked_access_token"
        assert response_json["token_type"] == "bearer"

        mock_authenticate.assert_awaited_once_with(db_session, "login_test@example.com", "password")
        mock_create_token.assert_called_once()
        call_args = mock_create_token.call_args[1]
        assert call_args["data"] == {"sub": str(mock_user.user_id), "type": "user"}
        assert "expires_delta" in call_args
        
    @pytest.mark.asyncio
    async def test_update_user(self, authenticated_user_client: AsyncClient, db_session, monkeypatch):
        update_data = {"age": 30, "height": 180.5, "weight": 75.0}
        mock_updated_user = models.User(
            user_id="AAAAA",
            **update_data,
            email="test@example.com",
            first_name="Test",
            last_name="User",
            role="user"
        )
        mock_update_user = AsyncMock(return_value=mock_updated_user)
        monkeypatch.setattr(crud, "update_user", mock_update_user)

        response = await authenticated_user_client.patch("/api/users/me", json=update_data)
        assert response.status_code == 200
        assert response.json()["age"] == update_data["age"]
        assert response.json()["height"] == update_data["height"]
        assert response.json()["weight"] == update_data["weight"]

    @pytest.mark.asyncio
    async def test_read_users_me(self, authenticated_user_client: AsyncClient, db_session):
        response = await authenticated_user_client.get("/api/users/me/")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_read_user_by_id(self, user_client: AsyncClient, db_session, monkeypatch):
        mock_user = models.User(user_id="AAAAA", email="test@example.com", first_name="Test", last_name="User", role="user")
        mock_get_user_by_id = AsyncMock(return_value=mock_user)
        monkeypatch.setattr(crud, "get_user_by_id", mock_get_user_by_id)

        response = await user_client.get("/api/users/byid/AAAAA")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_read_user_by_email(self, user_client: AsyncClient, db_session, monkeypatch):
        mock_user = models.User(user_id="AAAAA", email="test@example.com", first_name="Test", last_name="User", role="user")
        mock_get_user_by_email = AsyncMock(return_value=mock_user)
        monkeypatch.setattr(crud, "get_user_by_email", mock_get_user_by_email)

        response = await user_client.get("/api/users/byemail/test@example.com")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_delete_users_me(self, authenticated_user_client: AsyncClient, db_session, monkeypatch):
        mock_delete_user = AsyncMock(return_value=None)
        monkeypatch.setattr(crud, "delete_user", mock_delete_user)

        response = await authenticated_user_client.delete("/api/users/me/")
        assert response.status_code == 200
        assert "email" in response.json()

    @pytest.mark.asyncio
    async def test_request_trainer_user_mapping(self, authenticated_user_client: AsyncClient, db_session, monkeypatch):
        mock_db_mapping = AsyncMock()
        mock_db_mapping.id = 1
        mock_db_mapping.trainer_id = "AAAAA"
        mock_db_mapping.user_id = "AAAAA"
        mock_db_mapping.status = models.MappingStatus.pending
        mock_create_mapping = AsyncMock(return_value=mock_db_mapping)
        monkeypatch.setattr(crud, "create_trainer_user_mapping_request", mock_create_mapping)
        
        mapping_data = {"other_id": "AAAAA"}
        response = await authenticated_user_client.post("/api/trainer-user-mapping/request", json=mapping_data)
        
        assert response.status_code == 200
        assert response.json() == {
            "id": 1,
            "trainer_id": "AAAAA",
            "user_id": "AAAAA",
            "status": models.MappingStatus.pending.value
        }
        
    @pytest.mark.asyncio
    async def test_update_trainer_user_mapping_status(self, authenticated_user_client: AsyncClient, db_session, monkeypatch):
        mock_db_mapping = AsyncMock()
        mock_db_mapping.id = 1
        mock_db_mapping.trainer_id = "AAAAA"
        mock_db_mapping.user_id = "AAAAA"
        mock_db_mapping.status = models.MappingStatus.accepted
        mock_update_mapping = AsyncMock(return_value=mock_db_mapping)
        monkeypatch.setattr(crud, "update_trainer_user_mapping_status", mock_update_mapping)
        
        status_data = {"new_status": "accepted"}
        response = await authenticated_user_client.put("/api/trainer-user-mapping/1/status", json=status_data)
        
        assert response.status_code == 200
        assert response.json() == {
            "id": 1,
            "trainer_id": "AAAAA",
            "user_id": "AAAAA",
            "status": "accepted"
        }
        
    @pytest.mark.asyncio
    async def test_remove_specific_mapping(self, authenticated_user_client: AsyncClient, db_session, monkeypatch):
        mock_remove_mapping = AsyncMock(return_value=True)
        monkeypatch.setattr(crud, "remove_specific_mapping", mock_remove_mapping)

        response = await authenticated_user_client.delete("/api/trainer-user-mapping/2")
        assert response.status_code == 200
        assert "message" in response.json()