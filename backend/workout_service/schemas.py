from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict
from datetime import date, datetime
from enum import Enum

class QuestStatus(str, Enum):
    NOT_STARTED = "Not started"
    COMPLETED = "Completed"
    DEADLINE_PASSED = "Deadline passed"


class SessionIDMap(BaseModel):
    session_id: int
    workout_date: datetime
    member_id: str
    trainer_id: Optional[str]
    is_pt: bool
    session_type_id: int

class SessionCreate(BaseModel):
    member_id: str
    trainer_id: Optional[str] = None
    is_pt: bool
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
    
class QuestWorkoutSetCreate(BaseModel):
    set_number: int
    weight: float
    reps: int
    rest_time: int

class QuestWorkoutCreate(BaseModel):
    workout_key: int
    sets: List[QuestWorkoutSetCreate]

class QuestCreate(BaseModel):
    member_id: str
    workouts: List[QuestWorkoutCreate]

class QuestWorkoutSet(QuestWorkoutSetCreate):
    quest_id: int
    workout_key: int

class QuestWorkout(BaseModel):
    quest_id: int
    workout_key: int
    sets: List[QuestWorkoutSet]

class Quest(BaseModel):
    quest_id: int
    trainer_id: str
    member_id: str
    status: QuestStatus
    created_at: datetime
    workouts: List[QuestWorkout]

    class ConfigDict(ConfigDict):
        from_attributes = True
        
class workoutSet(BaseModel):
    set_number: int
    weight: float
    reps: int
    rest_time: int

class QuestWorkoutRecord(BaseModel):
    date: datetime
    sets: List[workoutSet]

class WorkoutName(BaseModel):
    workout_key: int
    workout_name: str
    
class WorkoutInfo(BaseModel):
    workout_key: int
    workout_name: str

class WorkoutsByPart(BaseModel):
    RootModel: Dict[str, List[WorkoutInfo]]