import asyncio
import pytest
import pytest_asyncio
import os
from httpx import AsyncClient, ASGITransport  # 추가된 부분
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from backend.user_service.database import Base, get_db
from backend.user_service.main import app
from backend.user_service import models  # 모델 import 추가

SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL_TEST")

@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(
        SQLALCHEMY_DATABASE_URL,
        poolclass=NullPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(autouse=True, scope="function")
async def session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        await cleanup_database(session)  # 세션 시작 전 데이터베이스 정리
        yield session
        # await session.close() # 이 줄을 제거합니다.

async def cleanup_database(session):
    # 모든 테이블 데이터 삭제
    for table in reversed(Base.metadata.sorted_tables):
        await session.execute(f"TRUNCATE TABLE {table.name} RESTART IDENTITY CASCADE")
    await session.commit()

@pytest.fixture
def test_app():
    return app

@pytest_asyncio.fixture
async def client(test_app, session):
    async def override_get_db():
        try:
            yield session
        finally:
            await session.close()

    test_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=test_app)  # 수정된 부분
    async with AsyncClient(transport=transport, base_url="http://test") as client:  # 수정된 부분
        yield client
    test_app.dependency_overrides.clear()

class BaseTestRouter:
    @pytest.fixture
    def app(self):
        raise NotImplementedError("Subclasses must implement this method")