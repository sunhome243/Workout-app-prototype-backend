from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class WorkoutKeyNameMap(Base):
    __tablename__ = "workout_key_name_mapping"
    workout_key = Column(Integer, primary_key=True)
    workout_name = Column(String, nullable=False)
    workout_part = Column(String, nullable=False)

class SessionIDMap(Base):
    __tablename__ = "session_id_mapping"
    session_id = Column(Integer, primary_key=True, index=True)
    session_type = Column(Integer, ForeignKey("session_type_map.session_type_id"))
    workout_date = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False)
    trainer_id = Column(Integer, nullable=True)
    is_pt = Column(String, nullable=False)

class SessionTypeMap(Base):
    __tablename__ = "session_type_map"
    session_type_id = Column(Integer, primary_key=True, index=True)
    session_type = Column(String, nullable=False)

class Session(Base):
    __tablename__ = "session"
    session_id = Column(Integer, ForeignKey("session_id_mapping.session_id"), primary_key=True)
    workout_key = Column(Integer, ForeignKey("workout_key_name_mapping.workout_key"), primary_key=True)
    set_num = Column(Integer, primary_key=True)
    weight = Column(Float, nullable=False)