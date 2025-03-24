from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# Completed Session Schemas
class CompletedSessionBase(BaseModel):
    date: datetime
    total_completed_drills: int
    total_drills: int
    drills: dict  # JSON data for drills

class CompletedSessionCreate(CompletedSessionBase):
    pass

class CompletedSession(CompletedSessionBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True



# Drill Group Schemas
class DrillGroupBase(BaseModel):
    name: str
    description: str
    drills: dict  # JSON data for drills
    is_liked_group: bool = False

class DrillGroupCreate(DrillGroupBase):
    pass

class DrillGroupUpdate(DrillGroupBase):
    name: Optional[str] = None
    description: Optional[str] = None
    drills: Optional[dict] = None
    is_liked_group: Optional[bool] = None

class DrillGroup(DrillGroupBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True



# Ordered Session Schemas
class DrillResponse(BaseModel):
    id: int
    title: str
    description: str
    type: str
    duration: Optional[int] = None
    sets: Optional[int] = None
    reps: Optional[int] = None
    equipment: List[str]
    suitable_locations: List[str]
    intensity: str
    difficulty: str
    instructions: List[str]
    tips: List[str]
    rest: Optional[int] = None

    class Config:
        from_attributes = True


class OrderedDrillBase(BaseModel):
    drill: DrillResponse
    sets_done: int = 0
    total_sets: int
    total_reps: int
    total_duration: int
    is_completed: bool = False

    class Config:
        from_attributes = True

class OrderedSessionDrillUpdate(BaseModel):
    ordered_drills: List[OrderedDrillBase]

    class Config:
        from_attributes = True 