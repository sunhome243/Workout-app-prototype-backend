import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from backend.user_service import schemas, models, crud, utils
from datetime import datetime, timedelta

pytestmark = pytest.mark.asyncio

class TestUserRouter:
    @pytest.mark.asyncio
    @patch("backend.user_service.crud.create_user")
    async def test_create_user(self, mock_create_user, user_client: AsyncClient, db_session):
        mock_user = models.User(
            user_id=1, 
            email="test@example.com", 
            first_name="Sunho", 
            last_name="Kim",
            role="user"
        )
        mock_create_user.return_value = mock_user
        
        data = {"email": "test@example.com", "password": "password", "first_name": "Sunho", "last_name": "Kim"}
        response = await user_client.post("/users/", json=data)
        assert response.status_code == 200
        assert response.json()["email"] == data["email"]
    
    @pytest.mark.asyncio
    @patch("backend.user_service.utils.create_access_token")
    @patch("backend.user_service.utils.authenticate_member")
    async def test_login_user(self, mock_authenticate, mock_create_token, user_client: AsyncClient, db_session):
        mock_user = models.User(
            user_id=1,
            email="login_test@example.com",
            first_name="Login",
            last_name="Test",
            role="user"
        )
        mock_authenticate.return_value = mock_user
        mock_create_token.return_value = "mocked_access_token"

        login_data = {"username": "login_test@example.com", "password": "password"}
        response = await user_client.post("/login", data=login_data)
        
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["access_token"] == "mocked_access_token"
        assert response.json()["token_type"] == "bearer"

        # Ensure that the mocked functions were called with correct arguments
        mock_authenticate.assert_called_once_with(db_session, "login_test@example.com", "password")
        mock_create_token.assert_called_once_with(
            data={"sub": "login_test@example.com", "role": "user"},
            expires_delta=pytest.approx(timedelta(minutes=30))  # Assuming ACCESS_TOKEN_EXPIRE_MINUTES is 30
        )
        
    @pytest.mark.asyncio
    @patch("backend.user_service.crud.update_user")
    async def test_update_user(self, mock_update_user, authenticated_user_client: AsyncClient, db_session):
        update_data = {"age": 30, "height": 180.5, "weight": 75.0}
        mock_update_user.return_value = models.User(
            user_id=1,  
            **update_data,
            email="test@example.com",
            first_name="Test",
            last_name="User",
            role="user"
        )
        response = await authenticated_user_client.patch("/users/me", json=update_data)
        assert response.status_code == 200
        assert response.json()["age"] == update_data["age"]
        assert response.json()["height"] == update_data["height"]
        assert response.json()["weight"] == update_data["weight"]

    async def test_read_users_me(self, authenticated_user_client: AsyncClient, db_session):
        response = await authenticated_user_client.get("/users/me/")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    @pytest.mark.asyncio
    @patch("backend.user_service.crud.get_user_by_id")
    async def test_read_user_by_id(self, mock_get_user_by_id, user_client: AsyncClient, db_session):
        mock_user = models.User(user_id=1, email="test@example.com", first_name="Test", last_name="User", role="user")
        mock_get_user_by_id.return_value = mock_user
        response = await user_client.get("/users/byid/1")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    @patch("backend.user_service.crud.get_user_by_email")
    async def test_read_user_by_email(self, mock_get_user_by_email, user_client: AsyncClient, db_session):
        mock_user = models.User(user_id=1, email="test@example.com", first_name="Test", last_name="User", role="user")
        mock_get_user_by_email.return_value = mock_user
        response = await user_client.get("/users/byemail/test@example.com")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    @pytest.mark.asyncio
    @patch("backend.user_service.crud.delete_user")
    async def test_delete_users_me(self, mock_delete_user, authenticated_user_client: AsyncClient, db_session):
        mock_delete_user.return_value = None
        response = await authenticated_user_client.delete("/users/me/")
        assert response.status_code == 200
        assert "email" in response.json()

    @pytest.mark.asyncio
    @patch("backend.user_service.crud.create_trainer_user_mapping_request")
    async def test_request_trainer_user_mapping(self, mock_create_mapping, authenticated_user_client: AsyncClient, db_session):
        mock_db_mapping = MagicMock()
        mock_db_mapping.id = 1
        mock_db_mapping.trainer_id = 2
        mock_db_mapping.user_id = 1
        mock_db_mapping.status = models.MappingStatus.pending
        mock_create_mapping.return_value = mock_db_mapping
        
        mapping_data = {"other_id": 2}
        response = await authenticated_user_client.post("/trainer-user-mapping/request", json=mapping_data)
        
        assert response.status_code == 200
        assert response.json() == {
            "id": 1,
            "trainer_id": 2,
            "user_id": 1,
            "status": models.MappingStatus.pending.value
        }
        
    @pytest.mark.asyncio
    @patch("backend.user_service.crud.update_trainer_user_mapping_status")
    async def test_update_trainer_user_mapping_status(self, mock_update_mapping, authenticated_user_client: AsyncClient, db_session):
        mock_db_mapping = MagicMock()
        mock_db_mapping.id = 1
        mock_db_mapping.trainer_id = 2
        mock_db_mapping.user_id = 1
        mock_db_mapping.status = models.MappingStatus.accepted
        mock_update_mapping.return_value = mock_db_mapping
        
        status_data = {"new_status": "accepted"}
        response = await authenticated_user_client.put("/trainer-user-mapping/1/status", json=status_data)
        
        assert response.status_code == 200
        assert response.json() == {
            "id": 1,
            "trainer_id": 2,
            "user_id": 1,
            "status": "accepted"
        }
        
    @pytest.mark.asyncio
    @patch("backend.user_service.crud.remove_specific_mapping")
    async def test_remove_specific_mapping(self, mock_remove_mapping, authenticated_user_client: AsyncClient, db_session):
        mock_remove_mapping.return_value = True
        response = await authenticated_user_client.delete("/trainer-user-mapping/2")
        assert response.status_code == 200
        assert "message" in response.json()