from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime

class SessionIDMap(BaseModel):
    session_id: int
    workout_date: date
    user_id: str
    trainer_id: Optional[str]
    is_pt: str
    session_type_id: int

class SessionCreate(BaseModel):
    workout_date: date
    user_id: str
    trainer_id: str | None
    is_pt: str
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
    
class QuestExerciseSetCreate(BaseModel):
    set_number: int
    weight: float
    reps: int
    rest_time: int

class QuestExerciseCreate(BaseModel):
    workout_key: int
    sets: List[QuestExerciseSetCreate]

class QuestCreate(BaseModel):
    user_id: str
    exercises: List[QuestExerciseCreate]

class QuestExerciseSet(QuestExerciseSetCreate):
    quest_id: int
    workout_key: int

class QuestExercise(BaseModel):
    quest_id: int
    workout_key: int
    sets: List[QuestExerciseSet]

class Quest(BaseModel):
    quest_id: int
    trainer_id: str
    user_id: str
    status: bool
    created_at: datetime
    exercises: List[QuestExercise]

    class ConfigDict(ConfigDict):
        from_attributes = True