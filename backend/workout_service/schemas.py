from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date

class SessionIDMap(BaseModel):
    session_id: int
    workout_date: date
    user_id: str
    trainer_id: Optional[str]
    is_pt: str
    session_type_id: int

class SessionCreate(BaseModel):
    workout_date: date
    user_id: str
    trainer_id: str | None
    is_pt: str
    session_type_id: int

class SetCreate(BaseModel):
    session_id: int
    workout_key: int
    set_num: int
    weight: float
    reps: int
    rest_time: int

class Session (BaseModel):
    session_id: int
    workout_key: int
    set_num: int
    weight: float
    reps: int
    rest_time: int

class SetResponse(SetCreate):
    pass

class SessionResponse(SessionCreate):
    session_id: int

class SessionWithSets(SessionResponse):
    sets: list[SetResponse]