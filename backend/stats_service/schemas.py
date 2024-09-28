# stats_service/schemas.py

from pydantic import BaseModel
from typing import List

class WeeklyProgressResponse(BaseModel):
    weeks: List[str]
    counts: List[int]
    goal: int