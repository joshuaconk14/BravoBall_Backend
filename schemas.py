from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime


# Completed Session Schemas
class CompletedSessionBase(BaseModel):
    date: datetime
    total_completed_drills: int
    total_drills: int
    drills: List[dict]  # List of drill data

class DrillData(BaseModel):
    uuid: str  # Use UUID instead of id
    title: str
    skill: str
    subSkills: List[str]
    sets: Optional[int] = None
    reps: Optional[int] = None
    duration: Optional[int] = None
    description: str
    instructions: List[str]
    tips: List[str]
    equipment: List[str]
    trainingStyle: str
    difficulty: str
    videoUrl: str

class CompletedDrillData(BaseModel):
    drill: DrillData
    setsDone: int
    totalSets: int
    totalReps: int
    totalDuration: int
    isCompleted: bool

class CompletedSessionCreate(BaseModel):
    date: str  # ISO8601 formatted string
    drills: List[CompletedDrillData]
    total_completed_drills: int
    total_drills: int

    model_config = ConfigDict(from_attributes=True)

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
    uuid: str  # Use UUID as primary identifier instead of id
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



class DrillSyncRequest(BaseModel):
    uuid: str  # Use UUID as primary identifier, required
    title: str

    model_config = ConfigDict(from_attributes=True)

class OrderedDrillSyncRequest(BaseModel):
    drill: DrillSyncRequest
    sets_done: int
    sets: int
    reps: int
    duration: int
    is_completed: bool = False

    model_config = ConfigDict(from_attributes=True)

class OrderedSessionDrillUpdate(BaseModel):
    ordered_drills: List[OrderedDrillSyncRequest]

    model_config = ConfigDict(from_attributes=True)



# Progress History Schemas
class ProgressHistoryBase(BaseModel):
    current_streak: int = 0
    previous_streak: int = 0  # Add previous_streak field
    highest_streak: int = 0
    completed_sessions_count: int = 0
    # ✅ NEW: Enhanced progress metrics
    favorite_drill: str = ''
    drills_per_session: float = 0.0
    minutes_per_session: float = 0.0
    total_time_all_sessions: int = 0
    dribbling_drills_completed: int = 0
    first_touch_drills_completed: int = 0
    passing_drills_completed: int = 0
    shooting_drills_completed: int = 0
    # ✅ NEW: Additional progress metrics
    most_improved_skill: str = ''
    unique_drills_completed: int = 0
    beginner_drills_completed: int = 0
    intermediate_drills_completed: int = 0
    advanced_drills_completed: int = 0

    model_config = ConfigDict(from_attributes=True)

class ProgressHistoryUpdate(ProgressHistoryBase):
    pass

class ProgressHistoryResponse(ProgressHistoryBase):
    id: int
    user_id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Saved Filters Schemas
