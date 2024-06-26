from typing import List, Union, Optional
from pydantic import BaseModel, Field, ConfigDict 


class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    user_id: int
    hashed_password: Optional[str] = None
    age: Optional[int] = Field(default=None)
    height: Optional[float] = Field(default=None)
    weight: Optional[float] = Field(default=None)
    exercise_duration: Optional[int] = Field(default=None)
    exercise_frequency: Optional[int] = Field(default=None)
    exercise_goal: Optional[int] = Field(default=None)
    exercise_level: Optional[int] = Field(default=None)
    usertype: Optional[str] = Field(default=None)

    class ConfigDict(ConfigDict):
        from_attributes = True
