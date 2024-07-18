from typing import List, Union, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum

class MemberBase(BaseModel):
    email: str
    first_name: str
    last_name: str
    @field_validator('email')
    def check_required_fields(cls, v):
        if v is None:
            raise ValueError(f'{cls.__name__} is a required field')
        return v

class MemberCreate(MemberBase):
    password: str
    @field_validator('password')
    def check_required_fields(cls, v):
        if v is None:
            raise ValueError(f'{cls.__name__} is a required field')
        return v

class Member(MemberBase):
    member_id: str
    age: Optional[int] = Field(default=None)
    height: Optional[float] = Field(default=None)
    weight: Optional[float] = Field(default=None)
    workout_level: Optional[int] = Field(default=None)
    workout_frequency: Optional[int] = Field(default=None)
    workout_goal: Optional[int] = Field(default=None)
    role: str
    
    class ConfigDict(ConfigDict):
        from_attributes = True

class MemberUpdate(BaseModel):
    current_password: Optional[str] = None
    new_password: Optional[str] = None
    confirm_password: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    workout_level: Optional[int] = None
    workout_frequency: Optional[int] = None
    workout_goal: Optional[int] = None

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
    trainer_id: str
    hashed_password: str
    role: str
    
class TrainerUpdate(BaseModel):
    current_password: Optional[str] = None
    new_password: Optional[str] = None
    confirm_password: Optional[str] = None

class ConnectedMemberInfo(BaseModel):
    member_id: str
    age: Optional[int]
    height: Optional[float]
    weight: Optional[float]
    workout_level: Optional[int]
    workout_frequency: Optional[int]
    workout_goal: Optional[int]
    first_name: Optional[str]
    last_name: Optional[str]

    class ConfigDict(ConfigDict):
        from_attributes = True
    
class MappingStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"

class MemberMappingInfo(BaseModel):
    member_id: str
    member_email: str
    member_first_name: str
    member_last_name: str
    status: MappingStatus

class TrainerMappingInfo(BaseModel):
    trainer_id: str
    trainer_email: str
    trainer_first_name: str
    trainer_last_name: str
    status: MappingStatus

class CreateTrainerMemberMapping(BaseModel):
    other_id: str

class TrainerMemberMappingResponse(BaseModel):
    id: int
    trainer_id: str
    member_id: str
    status: str

class TrainerMemberMappingUpdate(BaseModel):
    new_status: str

class Message(BaseModel):
    message: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Union[str, None] = None