from typing import List, Union, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str
    usertype: str
    
    @field_validator('password', 'usertype')
    def check_required_fields(cls, v):
        if v is None:
            raise ValueError(f'{cls.__name__} is a required field')
        return v
        
    @field_validator('usertype')
    def validate_usertype(cls, value):
        if value not in {'MEM', 'TRN'}:
            raise ValueError('usertype must be MEM or TRN')
        return value
    
    

class User(UserBase):
    user_id: int
    hashed_password: str
    age: Optional[int] = Field(default=None)
    height: Optional[float] = Field(default=None)
    weight: Optional[float] = Field(default=None)
    exercise_duration: Optional[int] = Field(default=None)
    exercise_frequency: Optional[int] = Field(default=None)
    exercise_goal: Optional[int] = Field(default=None)
    exercise_level: Optional[int] = Field(default=None)
    

    class ConfigDict(ConfigDict):
        from_attributes = True

class UserUpdate(UserBase):
    password: Optional[str] = Field(default=None)
    hashed_password: Optional[str] = Field(default=None)
    age: int 
    height: float 
    weight: float
    usertype: Optional[str] = Field(default=None)
    exercise_duration: Optional[int] = Field(default=1)
    exercise_frequency: Optional[int] = Field(default=1)
    exercise_goal: Optional[int] = Field(default=1)
    exercise_level: Optional[int] = Field(default=1)
    
    @field_validator('age', 'height', 'weight', 'usertype')
    def check_required_fields(cls, v):
        if v is None:
            raise ValueError(f'{cls.__name__} is a required field')
        return v
    
