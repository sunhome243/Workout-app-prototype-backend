import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.user_service.database import Base, get_db
from backend.user_service import main, cruds, models

# Override database URL for testing
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://postgres:Happy0702!@34.22.87.1/user_db_test"

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
def test_create_user(client: TestClient, testing_session: Session):
    user_data = {
        "email": "test@example.com",
        "password": "password",
        "height": 190.1
    }
    user_data2 = {
        "email": "test2@example.com",
        "password": "codingtesting",
        "height": 150.1
    }
    response = client.post("/users/", json=user_data)
    response2 = client.post("/users/", json=user_data2)
    assert response.status_code == 200
    assert response2.status_code == 200
    created_user = response.json()
    created_user2 = response2.json()
    assert created_user["email"] == user_data["email"]
    assert "user_id" in created_user
    assert created_user2["email"] == user_data2["email"]
    assert "user_id" in created_user2