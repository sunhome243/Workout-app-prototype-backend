import asyncio
import pytest
import pytest_asyncio
import os
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import text
from backend.user_service.database import Base, get_db
from backend.user_service.main import app

SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_USER_URL_TEST")

@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(
        SQLALCHEMY_DATABASE_URL,
        poolclass=NullPool
    )
    yield engine
    await engine.dispose()

async def cleanup_database(engine):
    async with engine.begin() as conn:
        # 모든 테이블 목록 가져오기
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = result.fetchall()

        # 외래 키 제약 조건 비활성화
        await conn.execute(text("SET CONSTRAINTS ALL DEFERRED"))

        # 모든 테이블 비우기
        for table in tables:
            await conn.execute(text(f"TRUNCATE TABLE {table[0]} RESTART IDENTITY CASCADE"))

        # 외래 키 제약 조건 다시 활성화
        await conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

        await conn.commit()

@pytest_asyncio.fixture(autouse=True, scope="function")
async def session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        await cleanup_database(engine)  # 세션 시작 전 데이터베이스 정리
        yield session
        await session.close()
        await cleanup_database(engine)  # 세션 종료 후 데이터베이스 정리

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
    transport = ASGITransport(app=test_app) 
    async with AsyncClient(transport=transport, base_url="http://test") as client: 
        yield client
    test_app.dependency_overrides.clear()

class BaseTestRouter:
    @pytest.fixture
    def app(self):
        raise NotImplementedError("Subclasses must implement this method")