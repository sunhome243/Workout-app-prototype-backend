import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# 현재 파일의 디렉토리 경로를 얻습니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
# 프로젝트 루트 디렉토리 경로를 얻습니다 (현재 디렉토리의 상위 디렉토리).
project_root = os.path.dirname(current_dir)
# .env 파일의 경로를 지정합니다.
dotenv_path = os.path.join(project_root, '.env')

# .env 파일을 로드합니다.
load_dotenv(dotenv_path)

# 환경 변수를 가져옵니다.
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("SQLALCHEMY_DATABASE_URL is not set in the environment or .env file")

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,
)

AsyncSession = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSession() as session:
        yield session