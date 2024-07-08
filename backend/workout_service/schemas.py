from typing import List, Union, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import date

class UserBase(BaseModel):
    user_id: int
    email: str

class User(UserBase):
    pass

class TrainerBase(BaseModel):
    trainer_id: int
    email: str

class Trainer(TrainerBase):
    pass


class WorkoutBase(BaseModel):
    workout_name: str
    workout_part: str

class WorkoutCreate(WorkoutBase):
    pass

class Workout(WorkoutBase):
    workout_key: int

    model_config = ConfigDict(from_attributes=True)

class SessionBase(BaseModel):
    workout_date: date
    user_id: int
    trainer_id: int
    is_pt: bool

class SessionCreate(SessionBase):
    pass

class Session(SessionBase):
    session_id: int

    model_config = ConfigDict(from_attributes=True)

class SessionDetailBase(BaseModel):
    workout_key: int
    set_num: int
    weight: float
    reps: int
    rest_time: int

class SessionDetailCreate(SessionDetailBase):
    pass

class SessionDetail(SessionDetailBase):
    session_id: int

    model_config = ConfigDict(from_attributes=True)