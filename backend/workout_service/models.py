from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum, Boolean, DateTime, UniqueConstraint, ForeignKeyConstraint
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from enum import Enum as PyEnum

Base = declarative_base()

class QuestStatus(PyEnum):
    NOT_STARTED = "Not started"
    COMPLETED = "Completed"
    DEADLINE_PASSED = "Deadline passed"

class Workouts(Base):
    __tablename__ = 'workouts'
    workout_id = Column(Integer, primary_key=True, autoincrement=True)
    workout_name = Column(String, nullable=False, unique=True)
    low_met = Column(Float, nullable=True)
    mid_met = Column(Float, nullable=True)
    high_met = Column(Float, nullable=True)
    sec_per_rep = Column(Float, nullable=True)
    # Relationship to WorkoutKeyNameMap
    workout_keys = relationship('WorkoutKeyNameMap', back_populates='workout')

class WorkoutParts(Base):
    __tablename__ = 'workout_parts'
    workout_part_id = Column(Integer, primary_key=True, autoincrement=True)
    workout_part_name = Column(String, nullable=False, unique=True)
    # Relationship to WorkoutKeyNameMap
    workout_keys = relationship('WorkoutKeyNameMap', back_populates='workout_part')

class WorkoutKeyNameMap(Base):
    __tablename__ = 'workout_key_name_map'
    workout_key_id = Column(Integer, primary_key=True, autoincrement=True)
    workout_id = Column(Integer, ForeignKey('workouts.workout_id'), nullable=False)
    workout_part_id = Column(Integer, ForeignKey('workout_parts.workout_part_id'), nullable=False)
    # Relationships
    workout = relationship('Workouts', back_populates='workout_keys')
    workout_part = relationship('WorkoutParts', back_populates='workout_keys')
    sessions = relationship('Session', back_populates='workout_key_name_map')

class SessionIDMap(Base):
    __tablename__ = "session_id_mapping"
    session_id = Column(Integer, primary_key=True, index=True)
    session_type_id = Column(Integer, ForeignKey("session_type_map.session_type_id"))
    workout_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    member_uid = Column(String, nullable=False)
    trainer_uid = Column(String, nullable=True)
    is_pt = Column(Boolean, nullable=False)
    quest_id = Column(Integer, ForeignKey('quests.quest_id'), nullable=True)
    # Relationships
    sessions = relationship('Session', back_populates='session_id_map')
    quest = relationship('Quest', back_populates='sessions')

class SessionTypeMap(Base):
    __tablename__ = "session_type_map"
    session_type_id = Column(Integer, primary_key=True, index=True)
    session_type = Column(String, nullable=False)

class Session(Base):
    __tablename__ = "session"
    session_id = Column(Integer, ForeignKey("session_id_mapping.session_id"), primary_key=True)
    workout_key = Column(Integer, ForeignKey("workout_key_name_map.workout_key_id"), primary_key=True)
    set_num = Column(Integer, primary_key=True)
    weight = Column(Float, nullable=False)
    reps = Column(Integer, nullable=False)
    rest_time = Column(Integer, nullable=False)
    # Relationships
    session_id_map = relationship('SessionIDMap', back_populates='sessions')
    workout_key_name_map = relationship('WorkoutKeyNameMap', back_populates='sessions')
    
class Quest(Base):
    __tablename__ = 'quests'
    quest_id = Column(Integer, primary_key=True, autoincrement=True)
    trainer_uid = Column(String, nullable=False)
    member_uid = Column(String, nullable=False)
    status = Column(Enum(QuestStatus), default=QuestStatus.NOT_STARTED) 
    workout_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Relationships
    workouts = relationship('QuestWorkout', back_populates='quest', cascade="all, delete-orphan")
    sessions = relationship('SessionIDMap', back_populates='quest')

class QuestWorkout(Base):
    __tablename__ = 'quest_workouts'
    quest_id = Column(Integer, ForeignKey('quests.quest_id'), primary_key=True)
    workout_key = Column(Integer, ForeignKey('workout_key_name_map.workout_key_id'), primary_key=True)
    # Relationships
    quest = relationship('Quest', back_populates='workouts')
    workout_key_name_map = relationship('WorkoutKeyNameMap')
    sets = relationship('QuestWorkoutSet', back_populates='workout', cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint('quest_id', 'workout_key', name='uq_quest_workout'),)

class QuestWorkoutSet(Base):
    __tablename__ = 'quest_workout_sets'
    quest_id = Column(Integer, primary_key=True)
    workout_key = Column(Integer, primary_key=True)
    set_number = Column(Integer, primary_key=True)
    weight = Column(Float, nullable=False)
    reps = Column(Integer, nullable=False)
    rest_time = Column(Integer, nullable=False)
    # Relationship
    workout = relationship('QuestWorkout', back_populates='sets')

    __table_args__ = (
        ForeignKeyConstraint(
            ['quest_id', 'workout_key'],
            ['quest_workouts.quest_id', 'quest_workouts.workout_key'],
            name='fk_quest_workout_set_workout'
        ),
    )