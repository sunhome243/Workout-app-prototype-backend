from sqlalchemy import Column, Integer, String, Float, Double, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.asyncio import AsyncAttrs
from enum import Enum as PyEnum

Base = declarative_base()

class User(Base, AsyncAttrs):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True, unique=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    height = Column(Double, nullable=True)
    weight = Column(Double, nullable=True)
    workout_duration = Column(Integer, nullable=True)
    workout_frequency = Column(Integer, nullable=True)
    workout_goal = Column(Integer, nullable=True)
    role = Column(String, default="user")

    # Relationship with TrainerUserMap
    trainer_mappings = relationship("TrainerUserMap", back_populates="user")


class Trainer(Base, AsyncAttrs):
    __tablename__ = "trainers"
    trainer_id = Column(Integer, primary_key=True, index=True, unique=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    role = Column(String, default="trainer")

    # Relationship with TrainerUserMap
    user_mappings = relationship("TrainerUserMap", back_populates="trainer")

class MappingStatus(PyEnum):
    pending = "pending"
    accepted = "accepted"

class TrainerUserMap(Base):
    __tablename__ = "trainer_user_mapping"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trainer_id = Column(Integer, ForeignKey("trainers.trainer_id"))
    user_id = Column(Integer, ForeignKey("users.user_id"))
    status = Column(SQLAlchemyEnum(MappingStatus), default=MappingStatus.pending)
    requester_id = Column(Integer)

    trainer = relationship("Trainer", back_populates="user_mappings")
    user = relationship("User", back_populates="trainer_mappings")


class WorkoutGoalMap(Base):
    __tablename__ = "workout_goal_mapping"
    workout_goal = Column(Integer, primary_key=True, index=True)
    workout_goal_name = Column(String, index=True)


class WorkoutDurationMap(Base):
    __tablename__ = "workout_duration_mapping"
    workout_duration = Column(Integer, primary_key=True, index=True)
    workout_duration_name = Column(String, index=True)


class WorkoutFrequencyMap(Base):
    __tablename__ = "workout_frequency_mapping"
    workout_frequency = Column(Integer, primary_key=True, index=True)
    workout_frequency_name = Column(String, index=True)
    
