from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date

class SessionIDMap(BaseModel):
    session_id: int
    workout_date: date
    user_id: int
    trainer_id: Optional[int]
    is_pt: str

class SessionCreate(BaseModel):
    workout_date: date
    user_id: int
    trainer_id: int | None
    is_pt: str

class Member(BaseModel):
    id: int
    email: str
    user_type: str

    class ConfigDict(ConfigDict):
        from_attributes = True