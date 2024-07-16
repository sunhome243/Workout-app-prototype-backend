from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Workouts(Base):
    __tablename__ = 'workouts'
    workout_id = Column(Integer, primary_key=True, autoincrement=True)
    workout_name = Column(String, nullable=False, unique=True)
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
    workout_date = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    trainer_id = Column(String, nullable=True)
    is_pt = Column(String, nullable=False)
    # Relationship
    sessions = relationship('Session', back_populates='session_id_map')

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