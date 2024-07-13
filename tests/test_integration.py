import pytest
from httpx import AsyncClient
from backend.user_service import models as user_models
from backend.workout_service import models as workout_models

pytestmark = pytest.mark.asyncio

class TestIntegration:
    async def test_user_workout_flow(self, user_client: AsyncClient, workout_client: AsyncClient):
        # 1. 사용자 생성
        user_data = {"email": "test@example.com", "password": "password", "first_name": "Test", "last_name": "User"}
        response = await user_client.post("/users/", json=user_data)
        assert response.status_code == 200
        user_id = response.json()["user_id"]

        # 2. 사용자 로그인
        login_data = {"username": "test@example.com", "password": "password"}
        response = await user_client.post("/login", data=login_data)
        assert response.status_code == 200
        access_token = response.json()["access_token"]

        # 3. 트레이너 생성
        trainer_data = {"email": "trainer@example.com", "password": "password", "first_name": "Test", "last_name": "Trainer"}
        response = await user_client.post("/trainers/", json=trainer_data)
        assert response.status_code == 200
        trainer_id = response.json()["trainer_id"]

        # 4. 트레이너 로그인
        trainer_login_data = {"username": "trainer@example.com", "password": "password"}
        response = await user_client.post("/login", data=trainer_login_data)
        assert response.status_code == 200
        trainer_token = response.json()["access_token"]

        # 5. 트레이너-사용자 매핑 요청
        mapping_data = {"other_id": trainer_id}
        response = await user_client.post("/trainer-user-mapping/request", json=mapping_data, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 200
        mapping_id = response.json()["id"]

        # 6. 트레이너가 매핑 수락
        status_data = {"new_status": "accepted"}
        response = await user_client.put(f"/trainer-user-mapping/{mapping_id}/status", json=status_data, headers={"Authorization": f"Bearer {trainer_token}"})
        assert response.status_code == 200

        # 7. 워크아웃 세션 생성
        session_data = {"user_id": user_id, "workout_date": "2023-07-14", "is_pt": "Y"}
        response = await workout_client.post("/create_session", json=session_data, headers={"Authorization": f"Bearer {trainer_token}"})
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # 8. 워크아웃 세션 조회
        response = await workout_client.get(f"/sessions/{session_id}", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 200
        assert response.json()["user_id"] == user_id
        assert response.json()["is_pt"] == "Y"

    async def test_unauthorized_access(self, workout_client: AsyncClient):
        # 인증되지 않은 사용자의 워크아웃 세션 생성 시도
        session_data = {"user_id": 1, "workout_date": "2023-07-14", "is_pt": "N"}
        response = await workout_client.post("/create_session", json=session_data)
        assert response.status_code == 401  # Unauthorized

    async def test_trainer_user_mismatch(self, user_client: AsyncClient, workout_client: AsyncClient):
        # 사용자 생성 및 로그인
        user_data = {"email": "mismatch@example.com", "password": "password", "first_name": "Mismatch", "last_name": "User"}
        response = await user_client.post("/users/", json=user_data)
        user_id = response.json()["user_id"]

        login_data = {"username": "mismatch@example.com", "password": "password"}
        response = await user_client.post("/login", data=login_data)
        access_token = response.json()["access_token"]

        # 다른 사용자의 워크아웃 세션 생성 시도
        session_data = {"user_id": user_id + 1, "workout_date": "2023-07-14", "is_pt": "N"}
        response = await workout_client.post("/create_session", json=session_data, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 403  # Forbidden

    async def test_user_profile_and_workout_integration(self, user_client: AsyncClient, workout_client: AsyncClient):
        # 사용자 생성
        user_data = {"email": "profile@example.com", "password": "password", "first_name": "Profile", "last_name": "User"}
        response = await user_client.post("/users/", json=user_data)
        user_id = response.json()["user_id"]

        # 로그인
        login_data = {"username": "profile@example.com", "password": "password"}
        response = await user_client.post("/login", data=login_data)
        access_token = response.json()["access_token"]

        # 사용자 프로필 업데이트
        update_data = {"age": 30, "height": 180.5, "weight": 75.0, "workout_duration": 60, "workout_frequency": 3, "workout_goal": 1}
        response = await user_client.patch("/users/me", json=update_data, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 200

        # 워크아웃 세션 생성
        session_data = {"user_id": user_id, "workout_date": "2023-07-14", "is_pt": "N"}
        response = await workout_client.post("/create_session", json=session_data, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # 워크아웃 세션 조회 및 사용자 프로필 정보 확인
        response = await workout_client.get(f"/sessions/{session_id}", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 200
        session_data = response.json()
        assert session_data["user_id"] == user_id
        assert session_data["user_profile"]["age"] == 30
        assert session_data["user_profile"]["height"] == 180.5
        assert session_data["user_profile"]["weight"] == 75.0