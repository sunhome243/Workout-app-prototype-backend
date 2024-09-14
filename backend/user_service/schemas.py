from typing import List, Union, Optional
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from datetime import datetime

class UserRole(str, Enum):
    member = "member"
    trainer = "trainer"

class UserCreate(BaseModel):
    uid: str
    email: str
    first_name: str
    last_name: str
    role: UserRole

class MemberBase(BaseModel):
    email: str
    first_name: str
    last_name: str

class MemberCreate(UserCreate):
    role: UserRole = UserRole.member

class Member(MemberBase):
    uid: str
    age: Optional[int] = Field(default=None)
    height: Optional[float] = Field(default=None)
    weight: Optional[float] = Field(default=None)
    workout_level: Optional[int] = Field(default=None)
    workout_frequency: Optional[int] = Field(default=None)
    workout_goal: Optional[int] = Field(default=None)
    role: UserRole = UserRole.member

    class Config:
        from_attributes = True

class MemberUpdate(BaseModel):
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    workout_level: Optional[int] = Field(None, ge=1, le=3)
    workout_frequency: Optional[int] = Field(None, ge=1, le=7)
    workout_goal: Optional[int] = Field(None, ge=1, le=3)
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class TrainerBase(BaseModel):
    email: str
    first_name: str
    last_name: str

class TrainerCreate(UserCreate):
    role: UserRole = UserRole.trainer

class Trainer(TrainerBase):
    uid: str
    role: UserRole = UserRole.trainer

    class Config:
        from_attributes = True

class TrainerUpdate(BaseModel):
    pass

class ConnectedMemberInfo(BaseModel):
    uid: str
    age: Optional[int]
    height: Optional[float]
    weight: Optional[float]
    workout_level: Optional[int]
    workout_frequency: Optional[int]
    workout_goal: Optional[int]
    first_name: Optional[str]
    last_name: Optional[str]

    class Config:
        from_attributes = True

class MappingStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    expired = "expired"

class MemberMappingInfo(BaseModel):
    mapping_id: int
    uid: str
    member_email: str
    member_first_name: str
    member_last_name: str
    status: MappingStatus

class MemberMappingInfoWithSessions(MemberMappingInfo):
    remaining_sessions: int

class TrainerMappingInfo(BaseModel):
    mapping_id: int
    uid: str
    trainer_email: str
    trainer_first_name: str
    trainer_last_name: str
    status: MappingStatus

class TrainerMappingInfoWithSessions(TrainerMappingInfo):
    remaining_sessions: int

class CreateTrainerMemberMapping(BaseModel):
    other_email: str  
    initial_sessions: int

class TrainerMemberMappingResponse(BaseModel):
    id: int
    trainer_uid: str
    member_uid: str
    status: MappingStatus
    remaining_sessions: int
    acceptance_date: Optional[datetime] = None

class TrainerMemberMappingUpdate(BaseModel):
    new_status: str

class Message(BaseModel):
    message: str

class RemainingSessionsResponse(BaseModel):
    remaining_sessions: int

class UpdateSessionsRequest(BaseModel):
    sessions_to_add: int
    
class SessionRequest(BaseModel):
    trainer_uid: str
    member_uid: str
    requested_sessions: int

class SessionRequestResponse(BaseModel):
    request_id: int
    status: str
    
class RequestMoreSessionsSchema(BaseModel):
    additional_sessions: int

class SessionRequestResponse(BaseModel):
    status: str  # 'approved' or 'rejected'