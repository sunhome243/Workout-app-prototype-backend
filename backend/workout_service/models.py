from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True, unique=True)
    email = Column(String, unique=True, index=True)

    # Relationship with TrainerUserMap
    trainer_user_maps = relationship("TrainerUserMap", back_populates="user")

class Trainer(Base):
    __tablename__ = "trainers"
    trainer_id = Column(Integer, primary_key=True, index=True, unique=True)
    email = Column(String, unique=True, index=True)

    # Relationship with TrainerUserMap
    trainer_user_maps = relationship("TrainerUserMap", back_populates="trainer")

class TrainerUserMap(Base):
    __tablename__ = "trainer_user_mapping"
    trainer_id = Column(Integer, ForeignKey('trainers.trainer_id', ondelete='CASCADE'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)

    trainer = relationship("Trainer", back_populates="trainer_user_maps")
    user = relationship("User", back_populates="trainer_user_maps")

class WorkoutKeyNameMap(Base):
    __tablename__ = "workout_key_name_mapping"
    workout_key = Column(Integer, primary_key=True)
    workout_name = Column(String, nullable=False)
    workout_part = Column(String, nullable=False)

class SessionIDMap(Base):
    __tablename__ = "session_id_mapping"
    session_id = Column(Integer, primary_key=True, index=True)
    workout_date = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False)
    trainer_id = Column(Integer, nullable=False)
    is_pt = Column(String, nullable=False)

class Session(Base):
    __tablename__ = "session"
    session_id = Column(Integer, ForeignKey("session_id_mapping.session_id"), primary_key=True)
    workout_key = Column(Integer, ForeignKey("workout_key_name_mapping.workout_key"), primary_key=True)
    set_num = Column(Integer, primary_key=True)
    weight = Column(Float, nullable=False)
    
