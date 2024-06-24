from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Float, Enum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class MemberBase(BaseModel):
    Mem_ID: int
    PW: str = Field(..., min_length=8, max_length=20)
    Age: int
    height: float
    weight: float
    Exercise_Duration: int
    Exercise_Frequency: int
    Exercise_Goal: int
    Exercise_Level: int
    Type: str

class MemberCreate(MemberBase):
    pass

class Member(MemberBase):
    class Config:
        orm_mode = True

class MemberDB(Base):
    __tablename__ = "member"

    Mem_ID = Column(Integer, primary_key=True, index=True)
    PW = Column(String(255))
    Age = Column(Integer)
    height = Column(Float)
    weight = Column(Float)
    Exercise_Duration = Column(Integer)
    Exercise_Frequency = Column(Integer)
    Exercise_Goal = Column(Integer)
    Exercise_Level = Column(Integer)
    Type = Column(String)
