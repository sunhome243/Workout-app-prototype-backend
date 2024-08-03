from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, ARRAY, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.asyncio import AsyncAttrs
from enum import Enum as PyEnum
from datetime import datetime


Base = declarative_base()

class UserRole(str, PyEnum):
    member = "member"
    trainer = "trainer"

class MappingStatus(str, PyEnum):
    pending = "pending"
    accepted = "accepted"
    expired = "expired"

class Member(Base, AsyncAttrs):
    __tablename__ = "members"
    uid = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    age = Column(Integer, nullable=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    workout_level = Column(Integer, nullable=True)
    workout_frequency = Column(Integer, nullable=True)
    workout_goal = Column(Integer, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.member)
    trainer_mappings = relationship("TrainerMemberMap", back_populates="member")
    fcm_tokens = Column(ARRAY(String), nullable=True)
    last_active = Column(DateTime, default=datetime.utcnow)

class Trainer(Base, AsyncAttrs):
    __tablename__ = "trainers"
    uid = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.trainer)
    member_mappings = relationship("TrainerMemberMap", back_populates="trainer")
    fcm_tokens = Column(ARRAY(String), nullable=True)
    last_active = Column(DateTime, default=datetime.utcnow)

class TrainerMemberMap(Base):
    __tablename__ = "trainer_member_mapping"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trainer_uid = Column(String, ForeignKey("trainers.uid"))
    member_uid = Column(String, ForeignKey("members.uid"))
    status = Column(SQLAlchemyEnum(MappingStatus), default=MappingStatus.pending)
    requester_uid = Column(String)
    remaining_sessions = Column(Integer, default=0)
    acceptance_date = Column(DateTime, nullable=True)
    trainer = relationship("Trainer", back_populates="member_mappings")
    member = relationship("Member", back_populates="trainer_mappings")
    
class WorkoutGoalMap(Base):
    __tablename__ = "workout_goal_mapping"
    workout_goal = Column(Integer, primary_key=True, index=True)
    workout_goal_name = Column(String, index=True)

class WorkoutlevelMap(Base):
    __tablename__ = "workout_level_mapping"
    workout_level = Column(Integer, primary_key=True, index=True)
    workout_level_name = Column(String, index=True)

class WorkoutFrequencyMap(Base):
    __tablename__ = "workout_frequency_mapping"
    workout_frequency = Column(Integer, primary_key=True, index=True)
    workout_frequency_name = Column(String, index=True)
    
class SessionRequest(Base):
    __tablename__ = "session_requests"

    id = Column(Integer, primary_key=True, index=True)
    trainer_uid = Column(String, ForeignKey("trainers.uid"))
    member_uid = Column(String, ForeignKey("members.uid"))
    requested_sessions = Column(Integer)
    status = Column(String)  # "pending", "approved", "rejected"
    created_at = Column(DateTime, default=datetime.utcnow)