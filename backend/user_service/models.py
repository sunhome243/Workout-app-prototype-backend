from sqlalchemy import Column, Integer, String, Float, ForeignKey, UniqueConstraint, func, select
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class EmailUniqueMixin:
    @validates('email')
    def validate_email(self, key, email):
        if isinstance(self, User):
            other = Trainer
        else:
            other = User
        
        # Check if email exists in the other table
        exists = select(func.count(other.id)).where(other.email == email)
        if self.session.execute(exists).scalar() > 0:
            raise ValueError("Email already exists in the other table")
        return email

class User(Base, EmailUniqueMixin):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    height = Column(Float, nullable=True)  # Changed from Double to Float
    weight = Column(Float, nullable=True)  # Changed from Double to Float
    workout_duration = Column(Integer, nullable=True)
    workout_frequency = Column(Integer, nullable=True)
    workout_goal = Column(Integer, nullable=True)
    role = Column(String, default="user")

    __table_args__ = (
        UniqueConstraint('email'),
    )

    # Relationship with TrainerUserMap
    trainer_user_maps = relationship("TrainerUserMap", back_populates="user")

class Trainer(Base, EmailUniqueMixin):
    __tablename__ = "trainers"
    trainer_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint('email'),
    )

    # Relationship with TrainerUserMap
    trainer_user_maps = relationship("TrainerUserMap", back_populates="trainer")

class TrainerUserMap(Base):
    __tablename__ = "trainer_user_mapping"
    trainer_id = Column(Integer, ForeignKey('trainers.trainer_id', ondelete='CASCADE'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    trainer = relationship("Trainer", back_populates="trainer_user_maps")
    user = relationship("User", back_populates="trainer_user_maps")

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