from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    exercise_duration = Column(Integer, nullable=True)
    exercise_frequency = Column(Integer, nullable=True)
    exercise_goal = Column(Integer, nullable=True)
    exercise_level = Column(Integer, nullable=True)
    usertype = Column(String, nullable=True)

