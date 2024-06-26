import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers, Session
from backend.user_service.database import Base, get_db, SQLALCHEMY_DATABASE_URL
from backend.user_service import main, cruds, models, schemas

# Override database URL for testing
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:itismepassword@localhost:5455/user-db-test"

# Create an engine and a SessionLocal class with a temporary database
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency for overriding the session
@pytest.fixture(scope="module")
def testing_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Override app creation for testing AFTER defining testing_session
main.app.dependency_overrides[get_db] = testing_session

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
        "password": "usingpassword",
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200
    created_user = response.json()
    assert created_user["email"] == user_data["email"]
    assert "user_id" in created_user

    # Cleanup: Delete the created user after the test
    db_user = cruds.get_user_by_email(testing_session, email=user_data["email"])
    if db_user:
        testing_session.delete(db_user)
        testing_session.commit()

# Clean up after testing
def cleanup():
    clear_mappers()
    Base.metadata.drop_all(bind=engine)

# Run cleanup function after all tests are done
def pytest_sessionfinish(session, exitstatus):
    cleanup()