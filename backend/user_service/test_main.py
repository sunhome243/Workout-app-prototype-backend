import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, drop_database

from main import app, get_db, Base
from models import MemberDB
import os

# Database URL for testing, obtained from environment variable or defaulting to local
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:itismepassword@localhost:5432/testing") 


# --- Test Setup and Teardown ---

def setup_module(module):
    """
    This function runs once before all tests in this module.
    It creates a clean test database and sets up the tables.
    """
    create_database(DATABASE_URL)  # Create the database

    # Connect to the newly created database
    test_engine = create_engine(DATABASE_URL) 
    Base.metadata.create_all(bind=test_engine)  # Create tables
    test_engine.dispose()  # Close the connection 

def teardown_module(module):
    """
    This function runs once after all tests in this module.
    It drops the test database to clean up.
    """
    drop_database(DATABASE_URL)

# --- Test Database Session ---

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=create_engine(DATABASE_URL))

# --- Test Client and Overrides --- 

@pytest.fixture(scope="module")
def client():
    """
    This fixture creates a test client for your FastAPI application
    and overrides the database dependency to use the test database.
    """
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

# --- Tests --- 

def test_create_member(client: TestClient): 
    """
    Test case to check if a new member can be created successfully.
    """
    member_data = {
        "PW": "password123",
        "Age": 30,
        "height": 180.5,
        "weight": 75.2,
        "Exercise_Duration": 60,
        "Exercise_Frequency": 3,
        "Exercise_Goal": 1,
        "Exercise_Level": 2,
        "Type": "MEM"
    }

    response = client.post("/members/", json=member_data) 

    assert response.status_code == 200  # Check if the request was successful
    response_data = response.json() 
    # Assert that the returned data matches the data sent in the request
    assert response_data["PW"] == member_data["PW"] 
    assert response_data["Age"] == member_data["Age"]
    assert response_data["height"] == member_data["height"]
    assert response_data["weight"] == member_data["weight"]
    assert response_data["Exercise_Duration"] == member_data["Exercise_Duration"]
    assert response_data["Exercise_Frequency"] == member_data["Exercise_Frequency"]
    assert response_data["Exercise_Goal"] == member_data["Exercise_Goal"]
    assert response_data["Exercise_Level"] == member_data["Exercise_Level"]
    assert response_data["Type"] == member_data["Type"]