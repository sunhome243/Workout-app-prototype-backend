from typing import List, Union, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

class UserBase(BaseModel):
    email: str
    @field_validator('email')
    def check_required_fields(cls, v):
        if v is None:
            raise ValueError(f'{cls.__name__} is a required field')
        return v

class UserCreate(UserBase):
    password: str
    
    @field_validator('password')
    def check_required_fields(cls, v):
        if v is None:
            raise ValueError(f'{cls.__name__} is a required field')
        return v
        
    
    

class User(UserBase):
    user_id: int
    hashed_password: str
    age: Optional[int] = Field(default=None)
    height: Optional[float] = Field(default=None)
    weight: Optional[float] = Field(default=None)
    workout_duration: Optional[int] = Field(default=None)
    workout_frequency: Optional[int] = Field(default=None)
    workout_goal: Optional[int] = Field(default=None)
    

    class ConfigDict(ConfigDict):
        from_attributes = True

class UserUpdate(UserBase):
    password: Optional[str] = Field(default=None)
    hashed_password: Optional[str] = Field(default=None)
    age: int 
    height: float 
    weight: float
    workout_duration: Optional[int] = Field(default=1)
    workout_frequency: Optional[int] = Field(default=1)
    workout_goal: Optional[int] = Field(default=1)
    
    @field_validator('age', 'height', 'weight')
    def check_required_fields(cls, v):
        if v is None:
            raise ValueError(f'{cls.__name__} is a required field')
        return v
    
