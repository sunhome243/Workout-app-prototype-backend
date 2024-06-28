from sqlalchemy import Column, Integer, String, Float, Double
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    height = Column(Double, nullable=True)
    weight = Column(Double, nullable=True)
    workout_duration = Column(Integer, nullable=True)
    workout_frequency = Column(Integer, nullable=True)
    workout_goal = Column(Integer, nullable=True)
