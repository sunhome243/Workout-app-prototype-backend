from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.asyncio import AsyncAttrs
from enum import Enum as PyEnum

Base = declarative_base()

class UserRole(str, PyEnum):
    member = "member"  
    trainer = "trainer"

class MappingStatus(str, PyEnum):
    pending = "pending"
    accepted = "accepted"

class Member(Base, AsyncAttrs): 
    __tablename__ = "members"  
    member_id = Column(String, primary_key=True, index=True, unique=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    workout_level = Column(Integer, nullable=True)
    workout_frequency = Column(Integer, nullable=True)
    workout_goal = Column(Integer, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.member)  # Changed default role to 'member'
    trainer_mappings = relationship("TrainerMemberMap", back_populates="member")  # Changed back_populates to 'member'

class Trainer(Base, AsyncAttrs):
    __tablename__ = "trainers"
    trainer_id = Column(String, primary_key=True, index=True, unique=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.trainer)
    member_mappings = relationship("TrainerMemberMap", back_populates="trainer")

class TrainerMemberMap(Base):
    __tablename__ = "trainer_member_mapping"  
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trainer_id = Column(String, ForeignKey("trainers.trainer_id"))
    member_id = Column(String, ForeignKey("members.member_id")) 
    status = Column(SQLAlchemyEnum(MappingStatus), default=MappingStatus.pending)
    requester_id = Column(String) 
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