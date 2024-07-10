from pydantic import BaseModel, ConfigDict
from typing import Optional

class SessionIDMap(BaseModel):
    session_id: int
    workout_date: str
    user_id: int
    trainer_id: Optional[int]
    is_pt: str

class Member(BaseModel):
    id: int
    email: str
    user_type: str

    class ConfigDict(ConfigDict):
        from_attributes = True