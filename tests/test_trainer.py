import pytest
from httpx import AsyncClient
from backend.user_service.main import app
from tests.conftest import BaseTestRouter

pytestmark = pytest.mark.asyncio

class TestUserRouter(BaseTestRouter):
    @pytest.fixture
    def app(self):
        return app

    async def test_create_trainer(self, client: AsyncClient, session):
        data2 = {"email": "trainertest@example.com", "password": "password", "first_name":"Sunho", "last_name":"Kim"}
        response2 = await client.post("/trainers/", json=data2)
        assert response2.status_code == 200
        assert response2.json()["email"] == data2["email"]

'''
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .database import Base, get_db
from . import main, crud, models
import os

# Override database URL for testing
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL_TEST")

# Create an engine and a SessionLocal class with a temporary database
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency for overriding the session
@pytest.fixture(scope="function")
def testing_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Clean up existing data
    cleanup_existing_data(session)

    yield session

    # Rollback transaction to clear data after test
    session.close()
    transaction.rollback()
    connection.close()

# Function to clean up existing data
def cleanup_existing_data(session):
    # Perform cleanup tasks here based on your application's requirements
    # For example, delete all users before running tests
    session.query(models.User).delete()
    session.commit()

# Define the client fixture
@pytest.fixture(scope="function")
def client(testing_session):
    def override_get_db():
        try:
            yield testing_session
        finally:
            testing_session.close()

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides = {}

# Test CRUD operations
def test_create_trainer(client: TestClient, testing_session: Session):
    # Create test data
    trainer_data = {
        "email": "test123@example.com",
        "password": "password",
        "first_name": "Sunho",
        "last_name": "Kim"
    }
    # Make a POST request to create the trainer
    response = client.post("/trainers/", json=trainer_data)
    
    # Assert the response
    assert response.status_code == 200
    created_trainer = response.json()
    assert created_trainer["email"] == trainer_data["email"]
    assert "trainer_id" in created_trainer

def test_get_trainer_byid(client: TestClient, testing_session: Session):
    # Create a trainer
    trainer_data = {
        "email": "test@example.com",
        "password": "password",
        "first_name": "itme",
        "last_name": "games"
    }
    response = client.post("/trainers/", json=trainer_data)
    assert response.status_code == 200
    created_trainer = response.json()

    # Test GET operation to retrieve the trainer
    response = client.get(f"/trainers/byid/{created_trainer['trainer_id']}")
    assert response.status_code == 200
    retrieved_trainer = response.json()
    assert retrieved_trainer["email"] == trainer_data["email"]
    assert retrieved_trainer["first_name"] == trainer_data["first_name"]
    assert retrieved_trainer["last_name"] == trainer_data["last_name"]

def test_get_trainer_byemail(client: TestClient, testing_session: Session):
    trainer_data = {
        "email": "test_trainer@example.com",
        "password": "password",
        "first_name": "John",
        "last_name": "Doe"
    }
    response = client.post("/trainers/", json=trainer_data)
    assert response.status_code == 200
    created_trainer = response.json()

    response = client.get(f"/trainers/byemail/{trainer_data['email']}")
    assert response.status_code == 200

    trainer = response.json()
    assert trainer["email"] == trainer_data["email"]
    assert trainer["first_name"] == trainer_data["first_name"]
    assert trainer["last_name"] == trainer_data["last_name"]

    response = client.get("/trainers/byemail/non_existent_email@example.com")
    assert response.status_code == 404
    assert response.json() == {"detail": "Trainer not found"}

# def test_get_trainers(client: TestClient, testing_session: Session):
#     # Create multiple trainers
#     trainer_data1 = {
#         "email": "test1@example.com",
#         "password": "password",
#         "first_name": "itme",
#         "last_name": "games"
#     }
#     trainer_data2 = {
#         "email": "test2@example.com",
#         "password": "password",
#         "first_name": "itme",
#         "last_name": "games"
#     }
#     client.post("/trainers/", json=trainer_data1)
#     client.post("/trainers/", json=trainer_data2)

#     # Test GET operation to retrieve trainers
#     response = client.get("/trainers/")
#     assert response.status_code == 200
#     trainers = response.json()
#     assert len(trainers) == 2

def test_update_trainer(client: TestClient, testing_session: Session):
    # Create a trainer to update
    trainer_data = {
        "email": "test@example.com",
        "password": "password",
        "first_name": "itme",
        "last_name": "games"
    }
    response = client.post("/trainers/", json=trainer_data)
    assert response.status_code == 200
    created_trainer = response.json()

    # Define update data
    trainer_update_data = {
        "email": "test@example.com",
        "password": "newpassword",
        "first_name": "itme",
        "last_name": "games"
    }

    # Make a PUT request to update the trainer
    update_response = client.put(f"/trainers/{created_trainer['trainer_id']}", json=trainer_update_data)
    assert update_response.status_code == 200

    # Test GET operation to retrieve the updated trainer
    response = client.get(f"/trainers/byid/{created_trainer['trainer_id']}")
    assert response.status_code == 200
    updated_trainer = response.json()
    assert updated_trainer["email"] == trainer_data["email"]
    

def test_trainer_user_map(client: TestClient, testing_session: Session):
    # Creating error
    mapping_data = {
        "trainer_id": 1,
        "user_id": 1
    }
    
    response = client.post("/trainer-user-mapping/", json=mapping_data)
    assert response.status_code == 404
    
    trainer_data = {
        "email": "test@example.com",
        "password": "password",
        "first_name": "itme",
        "last_name": "games"
    }
    response = client.post("/trainers/", json=trainer_data)
    assert response.status_code == 200
    created_trainer = response.json()
    
    user_data = {
        "email": "test23@example.com",
        "password": "password",
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200
    created_user = response.json()

    trainer_id = created_trainer['trainer_id']
    user_id = created_user['user_id']
    
    mapping_data = {
        "trainer_id": trainer_id,
        "user_id": user_id
    }
    
    # Make POST request to create mapping
    response = client.post("/trainer-user-mapping/", json=mapping_data)
    
    # Assert response status code
    assert response.status_code == 200
    
    # Assert response data matches expected schema (schemas.TrainerUserMap)
    created_mapping = response.json()
    assert created_mapping["trainer_id"] == mapping_data["trainer_id"]
    assert created_mapping["user_id"] == mapping_data["user_id"]
    
'''