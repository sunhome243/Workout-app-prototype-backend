import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from backend.user_service import schemas, models, crud

pytestmark = pytest.mark.asyncio

class TestUserRouter:
    async def test_create_user(self, user_client: AsyncClient):
        data = {"email": "test@example.com", "password": "password", "first_name": "Sunho", "last_name": "Kim"}
        response = await user_client.post("/users/", json=data)
        assert response.status_code == 200
        assert response.json()["email"] == data["email"]

    async def test_login_user(self, user_client: AsyncClient):
        # First, create a user
        user_data = {"email": "login_test@example.com", "password": "password", "first_name": "Login", "last_name": "Test"}
        await user_client.post("/users/", json=user_data)

        # Then, try to login
        login_data = {"username": "login_test@example.com", "password": "password"}
        response = await user_client.post("/login", data=login_data)
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"

    @patch("backend.user_service.crud.update_user")
    async def test_update_user(self, mock_update_user, authenticated_user_client: AsyncClient):
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

    async def test_read_users_me(self, authenticated_user_client: AsyncClient):
        response = await authenticated_user_client.get("/users/me/")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    @patch("backend.user_service.crud.get_user_by_id")
    async def test_read_user_by_id(self, mock_get_user_by_id, user_client: AsyncClient):
        mock_user = models.User(user_id=1, email="test@example.com", first_name="Test", last_name="User", role="user")
        mock_get_user_by_id.return_value = mock_user
        response = await user_client.get("/users/byid/1")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    @patch("backend.user_service.crud.get_user_by_email")
    async def test_read_user_by_email(self, mock_get_user_by_email, user_client: AsyncClient):
        mock_user = models.User(user_id=1, email="test@example.com", first_name="Test", last_name="User", role="user")
        mock_get_user_by_email.return_value = mock_user
        response = await user_client.get("/users/byemail/test@example.com")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    @patch("backend.user_service.crud.delete_user")
    async def test_delete_users_me(self, mock_delete_user, authenticated_user_client: AsyncClient):
        mock_delete_user.return_value = None
        response = await authenticated_user_client.delete("/users/me/")
        assert response.status_code == 200
        assert "email" in response.json()

    @patch("backend.user_service.crud.create_trainer_user_mapping_request")
    async def test_request_trainer_user_mapping(self, mock_create_mapping, authenticated_user_client: AsyncClient):
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

    @patch("backend.user_service.crud.update_trainer_user_mapping_status")
    async def test_update_trainer_user_mapping_status(self, mock_update_mapping, authenticated_user_client: AsyncClient):
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


    @patch("backend.user_service.crud.remove_specific_mapping")
    async def test_remove_specific_mapping(self, mock_remove_mapping, authenticated_user_client: AsyncClient):
        mock_remove_mapping.return_value = True
        response = await authenticated_user_client.delete("/trainer-user-mapping/2")
        assert response.status_code == 200
        assert "message" in response.json()