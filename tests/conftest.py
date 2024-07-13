import asyncio
import pytest
import pytest_asyncio
import os
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import text
from backend.user_service.database import Base as UserBase, get_db as get_user_db
from backend.user_service.main import app as user_app
from backend.workout_service.database import Base as WorkoutBase, get_db as get_workout_db
from backend.workout_service.main import app as workout_app
from backend.user_service import models, utils

@pytest_asyncio.fixture(scope="session")
async def engine_user():
    engine = create_async_engine(
        os.getenv("SQLALCHEMY_DATABASE_USER_URL_TEST"),
        poolclass=NullPool
    )
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="session")
async def engine_workout():
    engine = create_async_engine(
        os.getenv("SQLALCHEMY_DATABASE_WORKOUT_URL_TEST"),
        poolclass=NullPool
    )
    yield engine
    await engine.dispose()

async def cleanup_database(engine):
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = result.fetchall()
        await conn.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        for table in tables:
            await conn.execute(text(f"TRUNCATE TABLE {table[0]} RESTART IDENTITY CASCADE"))
        await conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        await conn.commit()

@pytest.fixture
def mock_current_user():
    return models.User(
        user_id=1,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        role="user",
        age=30,
        height=180.5,
        weight=75.0,
        workout_duration=60,
        workout_frequency=3,
        workout_goal=1
    )

@pytest.fixture
def mock_auth_token():
    return "test_token"

@pytest_asyncio.fixture(autouse=True, scope="function")
async def session_user(engine_user):
    async_session = sessionmaker(engine_user, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        await cleanup_database(engine_user)
        yield session
        await session.close()
        await cleanup_database(engine_user)

@pytest_asyncio.fixture(autouse=True, scope="function")
async def session_workout(engine_workout):
    async_session = sessionmaker(engine_workout, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        await cleanup_database(engine_workout)
        yield session
        await session.close()
        await cleanup_database(engine_workout)

@pytest.fixture
def test_user_app():
    return user_app

@pytest.fixture
def test_workout_app():
    return workout_app

@pytest_asyncio.fixture
async def user_client(test_user_app, session_user):
    async def override_get_db():
        try:
            yield session_user
        finally:
            await session_user.close()
    test_user_app.dependency_overrides[get_user_db] = override_get_db
    async with AsyncClient(app=test_user_app, base_url="http://test") as client:
        yield client
    test_user_app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def workout_client(test_workout_app, session_workout):
    async def override_get_db():
        try:
            yield session_workout
        finally:
            await session_workout.close()
    test_workout_app.dependency_overrides[get_workout_db] = override_get_db
    async with AsyncClient(app=test_workout_app, base_url="http://test") as client:
        yield client
    test_workout_app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def authenticated_user_client(test_user_app, user_client, mock_current_user, mock_auth_token):
    async def mock_get_current_member():
        return mock_current_user
    
    original_overrides = test_user_app.dependency_overrides.copy()
    test_user_app.dependency_overrides[utils.get_current_member] = mock_get_current_member
    
    headers = user_client.headers.copy()
    headers["Authorization"] = f"Bearer {mock_auth_token}"
    
    async with AsyncClient(app=test_user_app, base_url="http://test", headers=headers) as client:
        yield client
    
    test_user_app.dependency_overrides = original_overrides