import pytest
from httpx import AsyncClient
from backend.user_service.main import app
from tests.conftest import BaseTestRouter

pytestmark = pytest.mark.asyncio

class TestUserRouter(BaseTestRouter):
    async def test_create_user(self, client: AsyncClient, session):
        data = {"email": "test@example.com", "password": "password"}
        response = await client.post("/users/", json=data)
        assert response.status_code == 200
        assert response.json()["email"] == data["email"]
        
# # Override database URL for testing (use async database URL)
# SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL_TEST")

# # Create an async engine and a SessionLocal class with a temporary database
# engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
# TestingSessionLocal = sessionmaker(
#     engine, class_=AsyncSession, expire_on_commit=False
# )

# # Dependency for overriding the session
# @pytest.fixture(scope="function")
# async def testing_session():
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
    
#     async with TestingSessionLocal() as session:
#         yield session
#         await session.rollback()
    
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.drop_all)

# # Define the async client fixture
# @pytest.fixture(scope="function")
# async def async_client(testing_session):
#     async def override_get_db():
#         try:
#             yield testing_session
#         finally:
#             await testing_session.close()

#     main.app.dependency_overrides[get_db] = override_get_db
#     async with AsyncClient(app=main.app, base_url="http://test") as ac:
#         yield ac
#     main.app.dependency_overrides = {}

# Test CRUD operations


# @pytest.mark.asyncio
# async def test_get_user(async_client: AsyncClient, testing_session: AsyncSession):
#     # Create user first
#     user_data = {
#         "email": "test@example.com",
#         "password": "password",
#         "height": 190.1,
#     }
#     response = await async_client.post("/users/", json=user_data)
#     assert response.status_code == 200
#     created_user = response.json()

#     # Test get_user
#     user = await crud.get_user(testing_session, user_id=created_user["user_id"])
#     assert user
#     assert user.email == user_data["email"]

# @pytest.mark.asyncio
# async def test_update_user(async_client: AsyncClient, testing_session: AsyncSession):
#     # Create a user to update (initial creation)
#     user_data = {
#         "email": "test@example.com",
#         "password": "password",
#     }
#     response = await async_client.post("/users/", json=user_data)
#     assert response.status_code == 200
#     created_user = response.json()
    
#     # Define update data
#     user_update_data = {
#         "email": "test@example.com",
#         "password": "newpassword",
#         "age": 25,
#         "height": 170.0,
#         "weight": 65.0,
#     }
    
#     # Perform update operation
#     update_response = await async_client.put(f"/users/{created_user['user_id']}", json=user_update_data)
#     assert update_response.status_code == 200
    
#     # Check updated user in database
#     updated_user_id = created_user['user_id']
#     db_user = await testing_session.get(models.User, updated_user_id)
#     assert db_user.age == user_update_data['age']
#     assert db_user.height == user_update_data['height']
#     assert db_user.weight == user_update_data['weight']

# @pytest.mark.asyncio
# async def test_get_user_email(async_client: AsyncClient):
#     # 먼저 사용자 데이터를 생성합니다.
#     user_data = {
#         "email": "test_user@example.com",
#         "password": "password",
#     }
#     response = await async_client.post("/users/", json=user_data)
#     assert response.status_code == 200
#     created_user = response.json()

#     # 이메일로 사용자 정보를 가져오는 요청을 보냅니다.
#     response = await async_client.get(f"/users/byemail/{user_data['email']}")
#     assert response.status_code == 200

#     # 응답 데이터를 확인합니다.
#     user = response.json()
#     assert user["email"] == user_data["email"]

#     # 존재하지 않는 이메일로 요청을 보냅니다.
#     response = await async_client.get("/users/byemail/non_existent_email@example.com")
#     assert response.status_code == 404
#     assert response.json() == {"detail": "User not found"}

# @pytest.mark.asyncio
# async def test_login_and_get_token(async_client: AsyncClient):
#     user_data = {
#         "email": "test@example.com",
#         "password": "password",
#     }
#     response = await async_client.post("/users/", json=user_data)
#     assert response.status_code == 200    
    
#     login_data = {
#         "username": "test@example.com",  
#         "password": "password",          
#     }

#     login_response = await async_client.post("/login", data=login_data)
#     assert login_response.status_code == 200
#     token_data = login_response.json()
#     assert "access_token" in token_data
#     assert token_data["access_token"] is not None