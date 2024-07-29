import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock
from backend.user_service import schemas, models, crud, utils
from datetime import datetime, timedelta

class TestMemberRouter:
    @pytest.mark.asyncio
    async def test_create_member(self, user_client: AsyncClient, db_session, monkeypatch):
        mock_member = models.Member(
            member_uid="AAAAA", 
            email="test@example.com", 
            first_name="Sunho", 
            last_name="Kim",
            role="member"
        )
        mock_create_member = AsyncMock(return_value=mock_member)
        monkeypatch.setattr(crud, "create_member", mock_create_member)
        
        data = {"member_uid": "AAAAA", "email": "test@example.com", "password": "password", "first_name": "Sunho", "last_name": "Kim"}
        response = await user_client.post("/api/members/", json=data)
        assert response.status_code == 200
        assert response.json()["email"] == data["email"]
        assert response.json()["email"] == data["email"]
    
    @pytest.mark.asyncio
    async def test_login_member(self, user_client, db_session, monkeypatch):
        print(f"Type of user_client: {type(user_client)}")
        print(f"Attributes of user_client: {dir(user_client)}")
        mock_member = models.Member(
            member_uid="AAAAA",
            email="login_test@example.com",
            first_name="Login",
            last_name="Test",
            role="member"
        )
        mock_authenticate = AsyncMock(return_value=(mock_member, "member"))
        mock_create_token = MagicMock(return_value="mocked_access_token")
        monkeypatch.setattr(utils, "authenticate_member", mock_authenticate)
        monkeypatch.setattr(utils, "create_access_token", mock_create_token)

        login_data = {"username": "login_test@example.com", "password": "password"}
        response = await user_client.post("/login", data=login_data)

        assert response.status_code == 200
        response_json = response.json()
        assert "access_token" in response_json
        assert response_json["access_token"] == "mocked_access_token"
        assert response_json["token_type"] == "bearer"

        mock_authenticate.assert_awaited_once_with(db_session, "login_test@example.com", "password")
        mock_create_token.assert_called_once()
        call_args = mock_create_token.call_args[1]
        assert call_args["data"] == {"sub": str(mock_member.member_uid), "type": "member"}
        assert "expires_delta" in call_args
        
    @pytest.mark.asyncio
    async def test_update_member(self, authenticated_user_client: AsyncClient, db_session, monkeypatch):
        update_data = {"age": 30, "height": 180.5, "weight": 75.0}
        mock_updated_member = models.Member(
            member_uid="AAAAA",
            **update_data,
            email="test@example.com",
            first_name="Test",
            last_name="Member",
            role="member"
        )
        mock_update_member = AsyncMock(return_value=mock_updated_member)
        monkeypatch.setattr(crud, "update_member", mock_update_member)

        response = await authenticated_user_client.patch("/api/members/me", json=update_data)
        assert response.status_code == 200
        assert response.json()["age"] == update_data["age"]
        assert response.json()["height"] == update_data["height"]
        assert response.json()["weight"] == update_data["weight"]

    @pytest.mark.asyncio
    async def test_read_members_me(self, authenticated_user_client: AsyncClient, db_session):
        response = await authenticated_user_client.get("/api/members/me/")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_read_member_by_id(self, user_client: AsyncClient, db_session, monkeypatch):
        mock_member = models.Member(member_uid="AAAAA", email="test@example.com", first_name="Test", last_name="Member", role="member")
        mock_get_member_by_id = AsyncMock(return_value=mock_member)
        monkeypatch.setattr(crud, "get_member_by_id", mock_get_member_by_id)

        response = await user_client.get("/api/members/byid/AAAAA")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_read_member_by_email(self, user_client: AsyncClient, db_session, monkeypatch):
        mock_member = models.Member(member_uid="AAAAA", email="test@example.com", first_name="Test", last_name="Member", role="member")
        mock_get_member_by_email = AsyncMock(return_value=mock_member)
        monkeypatch.setattr(crud, "get_member_by_email", mock_get_member_by_email)

        response = await user_client.get("/api/members/byemail/test@example.com")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_delete_members_me(self, authenticated_user_client: AsyncClient, db_session, monkeypatch):
        mock_delete_member = AsyncMock(return_value=None)
        monkeypatch.setattr(crud, "delete_member", mock_delete_member)

        response = await authenticated_user_client.delete("/api/members/me/")
        assert response.status_code == 200
        assert "email" in response.json()
        
    
    @pytest.mark.asyncio
    async def test_request_trainer_member_mapping(self, authenticated_user_client: AsyncClient, db_session, monkeypatch):
        mock_db_mapping = AsyncMock()
        mock_db_mapping.id = 1
        mock_db_mapping.trainer_uid = "AAAAA"
        mock_db_mapping.member_uid = "AAAAA"
        mock_db_mapping.status = models.MappingStatus.pending
        mock_db_mapping.remaining_sessions = 10
        mock_create_mapping = AsyncMock(return_value=mock_db_mapping)
        monkeypatch.setattr(crud, "create_trainer_member_mapping_request", mock_create_mapping)
        
        mapping_data = {"other_id": "AAAAA", "initial_sessions": 10}
        response = await authenticated_user_client.post("/api/trainer-member-mapping/request", json=mapping_data)
        
        assert response.status_code == 200
        assert response.json() == {
            "id": 1,
            "trainer_uid": "AAAAA",
            "member_uid": "AAAAA",
            "status": models.MappingStatus.pending.value,
            "remaining_sessions": 10,
            'acceptance_date': None
        }


        
    @pytest.mark.asyncio
    async def test_update_trainer_member_mapping_status(self, authenticated_user_client: AsyncClient, db_session, monkeypatch):
        mock_db_mapping = AsyncMock()
        mock_db_mapping.id = 1
        mock_db_mapping.trainer_uid = "AAAAA"
        mock_db_mapping.member_uid = "BBBBB"
        mock_db_mapping.status = schemas.MappingStatus.accepted
        mock_db_mapping.remaining_sessions = 10
        mock_update_mapping = AsyncMock(return_value=mock_db_mapping)
        monkeypatch.setattr(crud, "update_trainer_member_mapping_status", mock_update_mapping)
        
        status_data = {"new_status": schemas.MappingStatus.accepted.value}
        response = await authenticated_user_client.patch("/api/trainer-member-mapping/1/status", json=status_data)
        
        assert response.status_code == 200
        assert response.json() == {
            "id": 1,
            "trainer_uid": "AAAAA",
            "member_uid": "BBBBB",
            "status": schemas.MappingStatus.accepted.value,
            "remaining_sessions": 10,
            'acceptance_date': '1970-01-01T00:00:01Z'
        }
        
    @pytest.mark.asyncio
    async def test_remove_specific_mapping(self, authenticated_user_client: AsyncClient, db_session, monkeypatch):
        mock_remove_mapping = AsyncMock(return_value=True)
        monkeypatch.setattr(crud, "remove_specific_mapping", mock_remove_mapping)

        response = await authenticated_user_client.delete("/api/trainer-member-mapping/2")
        assert response.status_code == 200
        assert "message" in response.json()
        
    @pytest.mark.asyncio
    async def test_remove_specific_mapping(self, authenticated_user_client: AsyncClient, db_session, monkeypatch):
        mock_remove_mapping = AsyncMock(return_value=True)
        monkeypatch.setattr(crud, "remove_specific_mapping", mock_remove_mapping)

        response = await authenticated_user_client.delete("/api/trainer-member-mapping/trainer_uid")
        assert response.status_code == 200
        assert "message" in response.json()

    @pytest.mark.asyncio
    async def test_remove_specific_mapping_multiple_members(self, authenticated_user_client: AsyncClient, db_session, monkeypatch):
        # Mock the current user (member)
        current_member = models.Member(member_uid="AAAAA", email="member1@example.com", role="member")
        monkeypatch.setattr(utils, "get_current_user", AsyncMock(return_value=current_member))

        # Mock the remove_specific_mapping function
        mock_remove_mapping = AsyncMock(return_value=True)
        monkeypatch.setattr(crud, "remove_specific_mapping", mock_remove_mapping)

        # Attempt to remove the mapping for the current member
        response = await authenticated_user_client.delete("/api/trainer-member-mapping/trainer1")

        assert response.status_code == 200
        assert "message" in response.json()
        assert "Successfully removed the trainer-member mapping" in response.json()["message"]

        # Verify that only the current member's mapping was removed
        mock_remove_mapping.assert_awaited_once_with(db_session, "AAAAA", "trainer1", False)

    @pytest.mark.asyncio
    async def test_remove_specific_mapping_success(self, authenticated_user_client: AsyncClient, db_session, monkeypatch):
        current_member = models.Member(member_uid="AAAAA", email="member1@example.com", role="member")
        monkeypatch.setattr(utils, "get_current_user", AsyncMock(return_value=current_member))
    
        # Mock get_trainer_by_id to return a trainer (simulating existing trainer)
        mock_get_trainer = AsyncMock(return_value=models.Trainer(trainer_uid="BBBBB", email="trainer@example.com"))
        monkeypatch.setattr(crud, "get_trainer_by_id", mock_get_trainer)
    
        # Mock remove_specific_mapping to return True (mapping successfully removed)
        mock_remove_mapping = AsyncMock(return_value=True)
        monkeypatch.setattr(crud, "remove_specific_mapping", mock_remove_mapping)
    
        response = await authenticated_user_client.delete("/api/trainer-member-mapping/BBBBB")
    
        assert response.status_code == 200
        assert "message" in response.json()
        assert "Successfully removed the trainer-member mapping" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_remove_specific_mapping_unauthorized(self, authenticated_user_client: AsyncClient, db_session, monkeypatch):
        # Mock the current user (member)
        current_member = models.Member(member_uid="AAAAA", email="member1@example.com", role="member")
        monkeypatch.setattr(utils, "get_current_user", AsyncMock(return_value=current_member))

        # Mock the remove_specific_mapping function to raise an exception
        mock_remove_mapping = AsyncMock(side_effect=ValueError("You are not authorized to remove this mapping"))
        monkeypatch.setattr(crud, "remove_specific_mapping", mock_remove_mapping)

        # Attempt to remove a mapping that doesn't belong to the current user
        response = await authenticated_user_client.delete("/api/trainer-member-mapping/unauthorized_trainer")

        assert response.status_code == 403
        assert "detail" in response.json()
        assert "You are not authorized to remove this mapping" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_trainer_member_mapping_status_unauthorized(self, authenticated_trainer_client: AsyncClient, db_session, monkeypatch):
        mock_update_mapping = AsyncMock(side_effect=ValueError("You are not authorized to update this mapping"))
        monkeypatch.setattr(crud, "update_trainer_member_mapping_status", mock_update_mapping)
    
        status_data = {"new_status": "accepted"}
        response = await authenticated_trainer_client.patch("/api/trainer-member-mapping/1/status", json=status_data)
    
        assert response.status_code == 400
        assert "detail" in response.json()
        assert "Invalid status: You are not authorized to update this mapping" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_remove_specific_mapping_success(self, authenticated_user_client: AsyncClient, db_session, monkeypatch):
        current_member = models.Member(member_uid="AAAAA", email="member1@example.com", role="member")
        monkeypatch.setattr(utils, "get_current_user", AsyncMock(return_value=current_member))
    
        # Mock get_trainer_by_id to return a trainer (simulating existing trainer)
        mock_get_trainer = AsyncMock(return_value=models.Trainer(trainer_uid="BBBBB", email="trainer@example.com"))
        monkeypatch.setattr(crud, "get_trainer_by_id", mock_get_trainer)
    
        # Mock remove_specific_mapping to return True (mapping successfully removed)
        mock_remove_mapping = AsyncMock(return_value=True)
        monkeypatch.setattr(crud, "remove_specific_mapping", mock_remove_mapping)
    
        response = await authenticated_user_client.delete("/api/trainer-member-mapping/ABABA")
    
        assert response.status_code == 200
        assert "message" in response.json()
        assert "Successfully removed the trainer-member mapping" in response.json()["message"]
