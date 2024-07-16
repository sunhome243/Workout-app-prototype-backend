import pytest
import pytest_asyncio
import os
import logging
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import text
from backend.user_service.database import Base as UserBase, get_db as get_user_db
from backend.user_service.main import app as user_app
from backend.workout_service.database import Base as WorkoutBase, get_db as get_workout_db
from backend.workout_service.main import app as workout_app
from backend.user_service import models, utils
from unittest.mock import patch

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Use in-memory SQLite for testing
DB_URL = os.getenv('TEST_DATABASE_URL', 'sqlite+aiosqlite:///:memory:')


@pytest_asyncio.fixture(scope="session")
async def engine():
    logger.info("Creating database engine")
    engine = create_async_engine(DB_URL, poolclass=NullPool, echo=True)
    
    async with engine.begin() as conn:
        logger.info("Creating tables for UserBase")
        await conn.run_sync(UserBase.metadata.create_all)
        logger.info("Creating tables for WorkoutBase")
        await conn.run_sync(WorkoutBase.metadata.create_all)
    
    await print_schema(engine)
    yield engine
    await engine.dispose()

async def clear_data(session: AsyncSession):
    logger.info("Clearing data from all tables")
    async with session.begin():
        for table in reversed(UserBase.metadata.sorted_tables):
            await session.execute(table.delete())
        for table in reversed(WorkoutBase.metadata.sorted_tables):
            await session.execute(table.delete())

@pytest_asyncio.fixture(scope="function")
async def db_session(engine):
    logger.info("Creating new database session")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        await clear_data(session)
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def user_client(db_session):
    async def override_get_db():
        yield db_session
    user_app.dependency_overrides[get_user_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=user_app), base_url="http://test") as client:
        yield client
    user_app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def workout_client(db_session):
    async def override_get_db():
        yield db_session
    workout_app.dependency_overrides[get_workout_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=workout_app), base_url="http://test") as client:
        yield client
    workout_app.dependency_overrides.clear()

@pytest.fixture
def mock_current_user():
    return models.User(
        user_id= "AAAAA",
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

@pytest_asyncio.fixture
async def authenticated_user_client(user_client, mock_current_user, mock_auth_token):
    async def mock_get_current_member():
        return mock_current_user
    
    user_app.dependency_overrides[utils.get_current_member] = mock_get_current_member
    headers = user_client.headers.copy()
    headers["Authorization"] = f"Bearer {mock_auth_token}"
    
    async with AsyncClient(transport=ASGITransport(app=user_app), base_url="http://test", headers=headers) as client:
        yield client
    
    user_app.dependency_overrides.clear()

async def print_schema(engine):
    logger.info("Printing database schema")
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = result.fetchall()
        logger.info("Database schema:")
        for table in tables:
            logger.info(f"- {table[0]}")
        
        # Print table details
        for table in tables:
            table_name = table[0]
            result = await conn.execute(text(f"PRAGMA table_info({table_name});"))
            columns = result.fetchall()
            logger.info(f"\nTable: {table_name}")
            for column in columns:
                logger.info(f"  - {column['name']} ({column['type']})")
                
@pytest.fixture
def mock_current_trainer():
    return models.Trainer(
        trainer_id="AAAAA",
        email="trainer@example.com",
        first_name="John",
        last_name="Doe",
        role="trainer",
        hashed_password="hashed_password"
    )

@pytest_asyncio.fixture
async def authenticated_trainer_client(user_client, mock_current_trainer, mock_auth_token):
    async def mock_get_current_member():
        return mock_current_trainer
    
    user_app.dependency_overrides[utils.get_current_member] = mock_get_current_member
    headers = user_client.headers.copy()
    headers["Authorization"] = f"Bearer {mock_auth_token}"
    
    async with AsyncClient(transport=ASGITransport(app=user_app), base_url="http://test", headers=headers) as client:
        yield client
    
    user_app.dependency_overrides.clear()
    
@pytest.fixture
def mock_auth():
    with patch("backend.workout_service.utils.get_current_member") as mock:
        mock.return_value = {"id": "user1", "user_type": "user"}
        yield mock