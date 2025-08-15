from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# *** PREMIUM SUBSCRIPTION ENUMS ***
class PremiumStatus(str, Enum):
    free = "free"
    premium = "premium"
    trial = "trial"
    expired = "expired"

class SubscriptionPlan(str, Enum):
    free = "free"
    monthly = "monthly"
    yearly = "yearly"
    lifetime = "lifetime"

class PremiumFeature(str, Enum):
    noAds = "noAds"
    unlimitedDrills = "unlimitedDrills"
    unlimitedCustomDrills = "unlimitedCustomDrills"
    unlimitedSessions = "unlimitedSessions"
    advancedAnalytics = "advancedAnalytics"
    basicDrills = "basicDrills"
    weeklySummaries = "weeklySummaries"
    monthlySummaries = "monthlySummaries"


# *** PREMIUM SUBSCRIPTION SCHEMAS ***
class PremiumStatusResponse(BaseModel):
    success: bool
    data: Dict[str, Any]

class PremiumSubscriptionBase(BaseModel):
    status: PremiumStatus
    plan: SubscriptionPlan
    startDate: datetime
    endDate: Optional[datetime] = None
    trialEndDate: Optional[datetime] = None
    isActive: bool
    features: List[str]

class PremiumStatusRequest(BaseModel):
    timestamp: int
    deviceId: str
    appVersion: str

class ReceiptVerificationRequest(BaseModel):
    platform: str  # 'ios' or 'android'
    receiptData: str
    productId: str
    transactionId: str

class ReceiptVerificationResponse(BaseModel):
    success: bool
    data: Dict[str, Any]



class FeatureAccessRequest(BaseModel):
    feature: str

class FeatureAccessResponse(BaseModel):
    success: bool
    data: Dict[str, Any]

class SubscriptionPlanDetails(BaseModel):
    plan: SubscriptionPlan
    name: str
    price: float
    currency: str
    durationDays: int
    description: Optional[str] = None
    features: List[str]
    isPopular: bool
    originalPrice: Optional[float] = None

class FreeFeatureUsage(BaseModel):
    customDrillsRemaining: int
    sessionsRemaining: int
    customDrillsUsed: int
    sessionsUsed: int

class PremiumSubscriptionDetails(BaseModel):
    id: int
    status: PremiumStatus
    plan: SubscriptionPlan
    startDate: datetime
    endDate: Optional[datetime] = None
    trialEndDate: Optional[datetime] = None
    isActive: bool
    isTrial: bool
    platform: Optional[str] = None
    receiptData: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Completed Session Schemas
class CompletedSessionBase(BaseModel):
    date: datetime
    session_type: str = 'drill_training'  # 'drill_training', 'mental_training', etc.
    
    # ✅ UPDATED: Optional drill-specific fields
    total_completed_drills: Optional[int] = None
    total_drills: Optional[int] = None
    drills: Optional[List[dict]] = None  # List of drill data (null for mental training)
    
    # ✅ NEW: Mental training specific fields
    duration_minutes: Optional[int] = None  # For mental training sessions
    mental_training_session_id: Optional[int] = None

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

# ✅ NEW: Drill training session creation
class CompletedDrillSessionCreate(BaseModel):
    date: str  # ISO8601 formatted string
    session_type: str = 'drill_training'
    drills: List[CompletedDrillData]
    total_completed_drills: int
    total_drills: int

    model_config = ConfigDict(from_attributes=True)

# ✅ NEW: Mental training session creation
class CompletedMentalTrainingSessionCreate(BaseModel):
    date: str  # ISO8601 formatted string
    session_type: str = 'mental_training'
    duration_minutes: int
    mental_training_session_id: int

    model_config = ConfigDict(from_attributes=True)

# ✅ UPDATED: Generic completed session creation (backwards compatible)
class CompletedSessionCreate(BaseModel):
    date: str  # ISO8601 formatted string    
    # Drill session fields (optional)
    drills: Optional[List[CompletedDrillData]] = None
    total_completed_drills: Optional[int] = None
    total_drills: Optional[int] = None
    session_type: Optional[str] = None

    
    # Mental training session fields (optional)
    duration_minutes: Optional[int] = None
    mental_training_session_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class CompletedSession(CompletedSessionBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)



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
    is_custom: bool = False  # ✅ NEW: Boolean to determine which table to search

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
    defending_drills_completed: int = 0
    goalkeeping_drills_completed: int = 0
    fitness_drills_completed: int = 0  # ✅ NEW: Add fitness drills completed
    # ✅ NEW: Additional progress metrics
    most_improved_skill: str = ''
    unique_drills_completed: int = 0
    beginner_drills_completed: int = 0
    intermediate_drills_completed: int = 0
    advanced_drills_completed: int = 0
    # ✅ NEW: Mental training metrics
    mental_training_sessions: int = 0
    total_mental_training_minutes: int = 0

    model_config = ConfigDict(from_attributes=True)

class ProgressHistoryUpdate(ProgressHistoryBase):
    pass

class ProgressHistoryResponse(ProgressHistoryBase):
    id: int
    user_id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Saved Filters Schemas
