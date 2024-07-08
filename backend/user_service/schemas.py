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
    role: str
    
    class ConfigDict(ConfigDict):
        from_attributes = True

class UserUpdate(BaseModel):
    current_password: Optional[str] = None
    new_password: Optional[str] = None
    confirm_password: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    workout_duration: Optional[int] = None
    workout_frequency: Optional[int] = None
    workout_goal: Optional[int] = None

    @field_validator('confirm_password')
    def passwords_match(cls, v, info):
        if 'new_password' in info.data:
            new_password = info.data['new_password']
            if new_password is not None and v != new_password:
                raise ValueError('Passwords do not match')
        return v

class TrainerBase(BaseModel):
    email: str
    first_name: str
    last_name: str
    def check_required_fields(cls, v):
        if v is None:
            raise ValueError(f'{cls.__name__} is a required field')
        return v

class TrainerCreate(TrainerBase):
    password: str
    
    @field_validator('password')
    def check_required_fields(cls, v):
        if v is None:
            raise ValueError(f'{cls.__name__} is a required field')
        return v

class Trainer(TrainerBase):
    trainer_id: int
    hashed_password: str
    role: str

class TrainerUpdate(TrainerBase):
    current_password: Optional[str] = None
    new_password: Optional[str] = None
    confirm_password: Optional[str] = None

class CreateTrainerUserMapping(BaseModel):
    other_id: int

class TrainerUserMappingResponse(BaseModel):
    trainer_id: int
    user_id: int

    class ConfigDict(ConfigDict):
        from_attributes = True

class Message(BaseModel):
    message: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Union[str, None] = None