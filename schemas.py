from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# User Preferences Schemas
class UserPreferencesBase(BaseModel):
    selected_time: Optional[str] = None
    selected_equipment: List[str] = []
    selected_training_style: Optional[str] = None
    selected_location: Optional[str] = None
    selected_difficulty: Optional[str] = None

class UserPreferencesCreate(UserPreferencesBase):
    pass

class UserPreferencesUpdate(UserPreferencesBase):
    pass

class UserPreferences(UserPreferencesBase):
    id: int
    user_id: int
    current_streak: int
    highest_streak: int
    completed_sessions_count: int

    class Config:
        from_attributes = True

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