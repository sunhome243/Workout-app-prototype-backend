# test_main.py

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, drop_database
from app.main import app, get_db
from app.models import Base, MemberDB

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:itismepassword@localhost/test_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def setup_module(module):
    create_database(SQLALCHEMY_DATABASE_URL)
    Base.metadata.create_all(bind=engine)

def teardown_module(module):
    drop_database(SQLALCHEMY_DATABASE_URL)

@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

# 테스트 함수: 회원 생성 테스트
def test_create_member(client: TestClient):
    member_data = {
        "Mem_ID": 1,
        "PW": "password123",
        "Age": 30,
        "height": 180.5,
        "weight": 75.2,
        "Exercise_Duration": 60,
        "Exercise_Frequency": 3,
        "Exercise_Goal": 1,
        "Exercise_Level": 2,
        "Type": "Trainer"
    }

    response = client.post("/members/", json=member_data)

    assert response.status_code == 200
    assert response.json()["Mem_ID"] == member_data["Mem_ID"]
    assert response.json()["Age"] == member_data["Age"]
    assert response.json()["height"] == member_data["height"]
    assert response.json()["weight"] == member_data["weight"]
    assert response.json()["Exercise_Duration"] == member_data["Exercise_Duration"]
    assert response.json()["Exercise_Frequency"] == member_data["Exercise_Frequency"]
    assert response.json()["Exercise_Goal"] == member_data["Exercise_Goal"]
    assert response.json()["Exercise_Level"] == member_data["Exercise_Level"]
    assert response.json()["Type"] == member_data["Type"]

