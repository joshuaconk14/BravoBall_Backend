"""
models.py
This defines all models used in chatbot app
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any, Union
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, JSON, ARRAY, Table, Float, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship
from db import Base
from enum import Enum
from sqlalchemy.sql import func
from datetime import datetime
from uuid import UUID
import uuid

# *** AUTH MODELS ***
class LoginRequest(BaseModel):
    email: str
    password: str

class EmailCheckRequest(BaseModel):
    email: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    email: str
    username: str
    refresh_token: Optional[str] = None
    avatar_path: Optional[str] = None
    avatar_background_color: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserInfoDisplay(BaseModel):
    email: str

    model_config = ConfigDict(from_attributes=True)


# *** MENTAL TRAINING MODELS ***
class MentalTrainingQuote(Base):
    __tablename__ = "mental_training_quotes"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    author = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'motivational', 'soccer_tip', 'mental_training'
    display_duration = Column(Integer, default=8)  # seconds to display
    created_at = Column(DateTime, server_default=func.now())

class MentalTrainingSession(Base):
    __tablename__ = "mental_training_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, server_default=func.now())
    duration_minutes = Column(Integer, nullable=False)
    session_type = Column(String, default="mental_training")
    
    # Relationship
    user = relationship("User", backref="mental_training_sessions")


# *** STORE ITEMS MODELS ***
class UserStoreItems(Base):
    __tablename__ = "user_store_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    treats = Column(Integer, default=0, nullable=False)
    streak_freezes = Column(Integer, default=0, nullable=False)
    streak_revivers = Column(Integer, default=0, nullable=False)
    # ✅ NEW: Streak freeze date - date when freeze is active
    active_freeze_date = Column(Date, nullable=True)
    # ✅ NEW: History of all freeze dates used/activated (stored as JSON array of ISO date strings)
    used_freezes = Column(JSON, default=list, nullable=False)
    # ✅ NEW: Streak reviver date - date when reviver was used
    active_streak_reviver = Column(Date, nullable=True)
    # ✅ NEW: History of all reviver dates used (stored as JSON array of ISO date strings)
    used_revivers = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="store_items")


class PurchaseTransaction(Base):
    __tablename__ = "purchase_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transaction_id = Column(String, unique=True, nullable=False, index=True)
    product_id = Column(String, nullable=False)
    treat_amount = Column(Integer, nullable=False)
    platform = Column(String, nullable=False)  # 'ios' or 'android'
    device_fingerprint = Column(String, nullable=True, index=True)  # Device fingerprint for security/audit
    app_version = Column(String, nullable=True)  # App version for audit purposes
    processed_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationship
    user = relationship("User", backref="purchase_transactions")


# *** USER AND USER DATA MODELS ***

class User(Base):
    __tablename__ = "users"

    # Registration / User ID
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    # Onboarding 
    primary_goal = Column(String)
    biggest_challenge = Column(JSON)  # Changed from String to JSON to store array
    training_experience = Column(String)
    position = Column(String)
    playstyle = Column(JSON)  # Changed from String to JSON to store array
    age_range = Column(String)
    strengths = Column(JSON)
    areas_to_improve = Column(JSON)
    training_location = Column(JSON)
    available_equipment = Column(JSON)
    daily_training_time = Column(String)
    weekly_training_days = Column(String)
    points = Column(Integer, default=0)
    
    # Profile customization
    avatar_path = Column(String, nullable=True)
    avatar_background_color = Column(String, nullable=True)  # Hex color code
    
    # Relationships
    completed_sessions = relationship("CompletedSession", back_populates="user")
    drill_groups = relationship("DrillGroup", back_populates="user")
    session_preferences = relationship("SessionPreferences", back_populates="user", uselist=False)
    progress_history = relationship("ProgressHistory", back_populates="user", uselist=False)
    saved_filters = relationship("SavedFilter", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    password_reset_codes = relationship("PasswordResetCode", back_populates="user")
    email_verification_codes = relationship("EmailVerificationCode", back_populates="user")
    store_items = relationship("UserStoreItems", back_populates="user", uselist=False)
    sent_friend_requests = relationship("Friendship", foreign_keys="[Friendship.requester_user_id]", back_populates="requester", cascade="all, delete-orphan")
    received_friend_requests = relationship("Friendship", foreign_keys="[Friendship.addressee_user_id]", back_populates="addressee", cascade="all, delete-orphan")

# Friendship model to support friend requests and relationships between users
class Friendship(Base):
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    requester_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    addressee_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    status = Column(String, default="pending") 
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships to User
    requester = relationship("User", foreign_keys=[requester_user_id], back_populates="sent_friend_requests")
    addressee = relationship("User", foreign_keys=[addressee_user_id], back_populates="received_friend_requests")


class CompletedSession(Base):
    __tablename__ = "completed_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime)
    
    # ✅ NEW: Session type for polymorphic sessions
    session_type = Column(String, default='drill_training')  # 'drill_training', 'mental_training', etc.
    
    # ✅ UPDATED: Make drill-specific fields nullable for mental training sessions
    total_completed_drills = Column(Integer, nullable=True)  # Null for mental training
    total_drills = Column(Integer, nullable=True)  # Null for mental training
    
    # ✅ UPDATED: Store session data as JSON (flexible for different session types)
    drills = Column(JSON, nullable=True)  # Null for mental training
    
    # ✅ NEW: Mental training specific fields (nullable for drill sessions)
    duration_minutes = Column(Integer, nullable=True)  # For mental training sessions
    mental_training_session_id = Column(Integer, ForeignKey("mental_training_sessions.id"), nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="completed_sessions")
    mental_training_session = relationship("MentalTrainingSession", backref="completed_session")



class OrderedSessionDrill(Base):
    __tablename__ = "ordered_session_drills"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("training_sessions.id"))  # Link to session
    drill_uuid = Column(PG_UUID(as_uuid=True), nullable=False)  # ✅ CHANGED: Use UUID instead of drill_id
    position = Column(Integer)  # Order in the session
    sets_done = Column(Integer)
    sets = Column(Integer, nullable=True)
    reps = Column(Integer, nullable=True)
    rest = Column(Integer, nullable=True)  # Per-session rest
    duration = Column(Integer, nullable=True)  # Per-session duration (if needed)
    is_completed = Column(Boolean, default=False)

    # Relationships
    session = relationship("TrainingSession", back_populates="ordered_drills")

# Remove direct relationship from User to OrderedSessionDrill
User.ordered_session_drills = None


class SessionPreferences(Base):
    __tablename__ = "session_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    duration = Column(Integer)  # in minutes
    available_equipment = Column(ARRAY(String))
    training_style = Column(String)
    training_location = Column(String)
    difficulty = Column(String)
    target_skills = Column(JSONB, default=list)  # List of {category: str, sub_skills: List[str]}
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    user = relationship("User", back_populates="session_preferences")



class DrillGroup(Base):
    __tablename__ = "drill_groups"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    description = Column(String)
    is_liked_group = Column(Boolean, default=False)  # To identify if this is the "Liked Drills" group
    
    # Relationships
    user = relationship("User", back_populates="drill_groups")
    drill_items = relationship("DrillGroupItem", back_populates="drill_group", cascade="all, delete-orphan")
    
    # ✅ UPDATED: Property to get drills using is_custom field for efficiency
    @property
    def drills(self):
        """
        Get all drills for this group by looking up UUIDs using the is_custom field.
        This is more efficient than checking both tables.
        """
        from sqlalchemy.orm import object_session
        from sqlalchemy import union_all, select, literal_column
        
        session = object_session(self)
        if not session:
            return []
        
        if not self.drill_items:
            return []
        
        # Get all UUIDs from drill items
        drill_uuids = [item.drill_uuid for item in self.drill_items if item.drill_uuid]
        
        if not drill_uuids:
            return []
        
        # Query both tables efficiently using UNION
        from models import Drill, CustomDrill
        
        # Query regular drills
        regular_drills = session.query(Drill).filter(Drill.uuid.in_(drill_uuids)).all()
        
        # Query custom drills
        custom_drills = session.query(CustomDrill).filter(CustomDrill.uuid.in_(drill_uuids)).all()
        
        # Combine results
        all_drills = regular_drills + custom_drills
        
        # Sort by the order in drill_items
        uuid_to_drill = {str(drill.uuid): drill for drill in all_drills}
        ordered_drills = []
        
        for item in self.drill_items:
            if item.drill_uuid and str(item.drill_uuid) in uuid_to_drill:
                ordered_drills.append(uuid_to_drill[str(item.drill_uuid)])
        
        return ordered_drills


# New junction table for many-to-many relationship between drill groups and drills
class DrillGroupItem(Base):
    __tablename__ = "drill_group_items"
    
    id = Column(Integer, primary_key=True, index=True)
    drill_group_id = Column(Integer, ForeignKey("drill_groups.id", ondelete="CASCADE"))
    drill_uuid = Column(PG_UUID(as_uuid=True), ForeignKey("drills.uuid", ondelete="CASCADE"))  # Changed from drill_id to drill_uuid
    position = Column(Integer)  # To maintain order of drills in a group
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    drill_group = relationship("DrillGroup", back_populates="drill_items")
    drill = relationship("Drill", foreign_keys=[drill_uuid])


# *** DRILL AND SESSION MODELS ***

class DrillCategory(Base):
    __tablename__ = "drill_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)


class DrillSkillFocus(Base):
    __tablename__ = "drill_skill_focus"
    
    id = Column(Integer, primary_key=True, index=True)
    drill_uuid = Column(PG_UUID(as_uuid=True), ForeignKey("drills.uuid"))
    category = Column(String)  # SkillCategory enum value
    sub_skill = Column(String)  # Corresponding SubSkill enum value
    is_primary = Column(Boolean, default=True)  # Whether this is a primary or secondary skill focus


class Drill(Base):
    __tablename__ = "drills"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(PG_UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid4, nullable=False)
    title = Column(String)
    description = Column(String)
    category_id = Column(Integer, ForeignKey("drill_categories.id"))
    
    # Time and Intensity
    duration = Column(Integer, nullable=True)  # in minutes, can be null for rep-based drills
    intensity = Column(String)  # high, medium, low
    training_styles = Column(JSON)  # List of TrainingStyle
    
    # Structure
    type = Column(String)  # DrillType enum
    sets = Column(Integer, nullable=True)
    reps = Column(Integer, nullable=True)
    rest = Column(Integer, nullable=True)  # in seconds
    
    # Requirements
    equipment = Column(JSON)  # List of Equipment
    suitable_locations = Column(JSON)  # List of Location
    
    # Technical
    difficulty = Column(String)
    
    # Content
    instructions = Column(JSON)  # List of steps
    tips = Column(JSON)  # List of coaching tips
    common_mistakes = Column(JSON)  # Things to watch out for
    progression_steps = Column(JSON)  # How to make it harder/easier
    variations = Column(JSON)  # Alternative versions
    video_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    
    # ✅ NEW: Custom drill identifier
    is_custom = Column(Boolean, default=False)  # False for default drills, True for custom drills

    # Relationships
    category = relationship("DrillCategory", backref="drills")
    skill_focus = relationship("DrillSkillFocus", foreign_keys="DrillSkillFocus.drill_uuid", primaryjoin="Drill.uuid == DrillSkillFocus.drill_uuid", backref="drill")  # Relationship to skill focus


class CustomDrill(Base):
    __tablename__ = "custom_drills"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(PG_UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Creator of the drill
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    
    # Time and Intensity
    duration = Column(Integer, nullable=True)  # in minutes, can be null for rep-based drills
    intensity = Column(String, nullable=True)  # high, medium, low
    training_styles = Column(JSON, nullable=True)  # List of TrainingStyle
    
    # Structure
    type = Column(String, nullable=True)  # DrillType enum
    sets = Column(Integer, nullable=True)
    reps = Column(Integer, nullable=True)
    rest = Column(Integer, nullable=True)  # in seconds
    
    # Requirements
    equipment = Column(JSON, nullable=True)  # List of Equipment
    suitable_locations = Column(JSON, nullable=True)  # List of Location
    
    # Technical
    difficulty = Column(String, nullable=True)
    
    # Content
    instructions = Column(JSON, nullable=True)  # List of steps
    tips = Column(JSON, nullable=True)  # List of coaching tips
    common_mistakes = Column(JSON, nullable=True)  # Things to watch out for
    progression_steps = Column(JSON, nullable=True)  # How to make it harder/easier
    variations = Column(JSON, nullable=True)  # Alternative versions
    video_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    
    # Skill focus (stored as JSON for simplicity)
    primary_skill = Column(JSON, nullable=True)  # {"category": "...", "sub_skill": "..."}
    # ✅ REMOVED: secondary_skills field since it's not being used
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # ✅ NEW: Custom drill identifier
    is_custom = Column(Boolean, default=True)  # "default" or "custom"
    
    # Relationships
    user = relationship("User", backref="custom_drills")


class TrainingSession(Base):
    """Represents a complete training session"""
    __tablename__ = "training_sessions"

    id = Column(Integer, primary_key=True, index=True)
    total_duration = Column(Integer)  # in minutes
    focus_areas = Column(JSON)  # List of skill areas
    created_at = Column(DateTime, server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional user association

    user = relationship("User", backref="training_sessions")

    # Add ordered_drills relationship
    ordered_drills = relationship("OrderedSessionDrill", back_populates="session")


# *** PYDANTIC MODELS FOR API REQUESTS/RESPONSES ***

class OnboardingData(BaseModel):
    # Required fields for authentication
    email: str
    username: Optional[str] = None
    password: str

    # Optional onboarding fields
    primaryGoal: Optional[str] = None
    trainingExperience: Optional[str] = None
    position: Optional[str] = None
    ageRange: Optional[str] = None
    strengths: Optional[List[str]] = []
    areasToImprove: Optional[List[str]] = []
    biggestChallenge: Optional[List[str]] = []
    playstyle: Optional[List[str]] = []
    trainingLocation: Optional[List[str]] = []
    availableEquipment: Optional[List[str]] = ["ball"]  # Default to just a soccer ball
    dailyTrainingTime: Optional[str] = "30"  # Default to 30 minutes
    weeklyTrainingDays: Optional[str] = "moderate"  # Default to moderate schedule

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )



class SkillFocusModel(BaseModel):
    category: str
    sub_skill: str
    is_primary: bool = False

    model_config = ConfigDict(from_attributes=True)


class SessionPreferencesRequest(BaseModel):
    duration: int
    available_equipment: List[str]
    training_style: str
    training_location: str
    difficulty: str
    target_skills: List[Dict[str, Union[str, List[str]]]]  # [{category: str, sub_skills: List[str]}]

    model_config = ConfigDict(from_attributes=True)


class DrillRequest(BaseModel):
    title: str
    description: str
    type: str  # DrillType enum value
    duration: Optional[int] = None
    sets: Optional[int] = None
    reps: Optional[int] = None
    rest: Optional[int] = None
    equipment: List[str]
    suitable_locations: List[str]
    intensity: str
    training_styles: List[str]
    difficulty: str
    primary_skill: Dict[str, str]  # {"category": "...", "sub_skill": "..."}
    secondary_skills: List[Dict[str, str]] = []  # [{"category": "...", "sub_skill": "..."}]
    instructions: List[str]
    tips: List[str]
    common_mistakes: List[str] = []
    progression_steps: List[str] = []
    variations: List[str] = []
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DrillResponse(BaseModel):
    uuid: str  # Use UUID instead of id
    title: str
    description: str
    type: str
    duration: Optional[int] = None
    sets: Optional[int] = None
    reps: Optional[int] = None
    rest: Optional[int] = None
    equipment: List[str]
    suitable_locations: List[str]
    intensity: str
    training_styles: List[str]
    difficulty: str
    primary_skill: Dict[str, str]
    secondary_skills: List[Dict[str, str]] = []
    instructions: List[str]
    tips: List[str]
    common_mistakes: List[str] = []
    progression_steps: List[str] = []
    variations: List[str] = []
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_custom: bool = False  # ✅ NEW: Custom drill identifier

    model_config = ConfigDict(from_attributes=True)


class CustomDrillCreate(BaseModel):
    title: str
    description: str
    type: Optional[str] = None
    duration: Optional[int] = None
    sets: Optional[int] = None
    reps: Optional[int] = None
    rest: Optional[int] = None
    equipment: Optional[List[str]] = None
    suitable_locations: Optional[List[str]] = None
    intensity: Optional[str] = None
    training_styles: Optional[List[str]] = None
    difficulty: Optional[str] = None
    primary_skill: Optional[Dict[str, str]] = None  # {"category": "...", "sub_skill": "..."}
    # ✅ REMOVED: secondary_skills field since it's not being used
    instructions: Optional[List[str]] = []
    tips: Optional[List[str]] = None
    common_mistakes: Optional[List[str]] = None
    progression_steps: Optional[List[str]] = None
    variations: Optional[List[str]] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CustomDrillResponse(BaseModel):
    uuid: str
    title: str
    description: str
    type: Optional[str] = None
    duration: Optional[int] = None
    sets: Optional[int] = None
    reps: Optional[int] = None
    rest: Optional[int] = None
    equipment: Optional[List[str]] = None
    suitable_locations: Optional[List[str]] = None
    intensity: Optional[str] = None
    training_styles: Optional[List[str]] = None
    difficulty: Optional[str] = None
    primary_skill: Optional[Dict[str, str]] = None
    # ✅ REMOVED: secondary_skills field since it's not being used
    instructions: Optional[List[str]] = []
    tips: Optional[List[str]] = None
    common_mistakes: Optional[List[str]] = None
    progression_steps: Optional[List[str]] = None
    variations: Optional[List[str]] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_custom: bool = True  # ✅ NEW: Custom drill identifier

    model_config = ConfigDict(from_attributes=True)


class DrillListResponse(BaseModel):
    drills: List[DrillResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    session_id: Optional[int] = None
    total_duration: int
    focus_areas: List[str]
    drills: List[DrillResponse]

    model_config = ConfigDict(from_attributes=True)


class CompletedSessionRequest(BaseModel):
    date: str  # ISO format date string
    total_completed_drills: int
    total_drills: int
    drills: List[DrillResponse]

    model_config = ConfigDict(from_attributes=True)


class CompletedSessionResponse(BaseModel):
    id: int
    date: str  # ISO format date string
    total_completed_drills: int
    total_drills: int
    drills: List[DrillResponse]

    model_config = ConfigDict(from_attributes=True)


class DrillGroupRequest(BaseModel):
    name: str
    description: str
    drill_uuids: List[str] = []  # Changed from drill_ids to drill_uuids
    is_liked_group: bool = False

    model_config = ConfigDict(from_attributes=True)


class DrillGroupResponse(BaseModel):
    id: int
    name: str
    description: str
    drills: List[DrillResponse]
    is_liked_group: bool

    model_config = ConfigDict(from_attributes=True)
    

# *** ONBOARDING ENUMS ***
class PrimaryGoal(str, Enum):
    IMPROVE_SKILL = "improve_skill"
    BEST_ON_TEAM = "best_on_team"
    COLLEGE_SCOUTING = "college_scouting"
    GO_PRO = "go_pro"
    IMPROVE_FITNESS = "improve_fitness"
    HAVE_FUN = "have_fun"

class Challenge(str, Enum):
    LACK_OF_TIME = "lack_of_time"
    LACK_OF_EQUIPMENT = "lack_of_equipment"
    UNSURE_FOCUS = "unsure_focus"
    MOTIVATION = "motivation"
    INJURY = "injury"
    NO_TEAM = "no_team"

class ExperienceLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    PROFESSIONAL = "professional"

class Position(str, Enum):
    GOALKEEPER = "goalkeeper"
    FULLBACK = "fullback"
    CENTER_BACK = "center_back"
    DEFENSIVE_MID = "defensive_mid"
    CENTER_MID = "center_mid"
    ATTACKING_MID = "attacking_mid"
    WINGER = "winger"
    STRIKER = "striker"

class AgeRange(str, Enum):
    YOUTH = "youth"
    TEEN = "teen"
    JUNIOR = "junior"
    ADULT = "adult"
    SENIOR = "senior"

class Skill(str, Enum):
    PASSING = "passing"
    DRIBBLING = "dribbling"
    SHOOTING = "shooting"
    DEFENDING = "defending"
    FIRST_TOUCH = "first_touch"
    FITNESS = "fitness"

class TrainingLocation(str, Enum):
    FULL_FIELD = "full_field"
    SMALL_FIELD = "small_field"
    INDOOR_COURT = "indoor_court"
    BACKYARD = "backyard"
    SMALL_ROOM = "small_room"

class Equipment(str, Enum):
    BALL = "ball"
    CONES = "cones"
    WALL = "wall"
    GOALS = "goals"

class TrainingDuration(int, Enum):
    MINS_15 = 15
    MINS_30 = 30
    MINS_45 = 45
    MINS_60 = 60
    MINS_90 = 90
    MINS_120 = 120

class TrainingFrequency(str, Enum):
    LIGHT = "light"
    MODERATE = "moderate"
    INTENSE = "intense"

class TrainingStyle(str, Enum):
    LOW_INTENSITY = "low_intensity"
    MEDIUM_INTENSITY = "medium_intensity"
    HIGH_INTENSITY = "high_intensity"

class Difficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

# *** SKILL CATEGORY ENUMS ***
class SkillCategory(str, Enum):
    PASSING = "passing"
    SHOOTING = "shooting"
    DRIBBLING = "dribbling"
    FIRST_TOUCH = "first_touch"
    DEFENDING = "defending"
    GOALKEEPING = "goalkeeping"
    FITNESS = "fitness"

class PassingSubSkill(str, Enum):
    SHORT_PASSING = "short_passing"
    LONG_PASSING = "long_passing"
    WALL_PASSING = "wall_passing"

class ShootingSubSkill(str, Enum):
    POWER = "power"
    FINISHING = "finishing"
    VOLLEYS = "volleys"
    LONG_SHOTS = "long_shots"
    DRIVEN_SHOTS = "driven_shots"
    BALL_STRIKING = "ball_striking"

class DribblingSubSkill(str, Enum):
    BALL_MASTERY = "ball_mastery"
    CLOSE_CONTROL = "close_control"
    SPEED_DRIBBLING = "speed_dribbling"
    ONE_V_ONE_MOVES = "1v1_moves"

class FirstTouchSubSkill(str, Enum):
    GROUND_CONTROL = "ground_control"
    AERIAL_CONTROL = "aerial_control"
    TURNING_WITH_BALL = "turning_with_ball"
    ONE_TOUCH_CONTROL = "one_touch_control"

class DefendingSubSkill(str, Enum):
    TACKLING = "tackling"
    MARKING = "marking"
    INTERCEPTING = "intercepting"
    JOCKEYING = "jockeying"
    AERIAL_DEFENDING = "aerial_defending"

class GoalkeepingSubSkill(str, Enum):
    HAND_EYE_COORDINATION = "hand_eye_coordination"
    DIVING = "diving"
    REFLEXES = "reflexes"
    SHOT_STOPPING = "shot_stopping"
    POSITIONING = "positioning"
    CATCHING = "catching"

class FitnessSubSkill(str, Enum):
    SPEED = "speed"
    AGILITY = "agility"
    ENDURANCE = "endurance"

class DrillType(str, Enum):
    TIME_BASED = "time_based"  # e.g., "Perform for 2 minutes"
    REPS_BASED = "reps_based"  # e.g., "Do 10 shots"
    SET_BASED = "set_based"    # e.g., "3 sets of 5 reps"
    CONTINUOUS = "continuous"  # e.g., "Until successful completion"

class ProgressHistory(Base):
    __tablename__ = "progress_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    current_streak = Column(Integer, default=0)
    previous_streak = Column(Integer, default=0)  # Add previous_streak field
    highest_streak = Column(Integer, default=0)
    completed_sessions_count = Column(Integer, default=0)
    # ✅ NEW: Enhanced progress metrics
    favorite_drill = Column(String, default='', nullable=True)
    drills_per_session = Column(Float, default=0.0)
    minutes_per_session = Column(Float, default=0.0)
    total_time_all_sessions = Column(Integer, default=0)
    dribbling_drills_completed = Column(Integer, default=0)
    first_touch_drills_completed = Column(Integer, default=0)
    passing_drills_completed = Column(Integer, default=0)
    shooting_drills_completed = Column(Integer, default=0)
    defending_drills_completed = Column(Integer, default=0)
    goalkeeping_drills_completed = Column(Integer, default=0)
    fitness_drills_completed = Column(Integer, default=0)  # ✅ NEW: Add fitness drills completed
    # ✅ NEW: Additional progress metrics
    most_improved_skill = Column(String, default='', nullable=True)
    unique_drills_completed = Column(Integer, default=0)
    beginner_drills_completed = Column(Integer, default=0)
    intermediate_drills_completed = Column(Integer, default=0)
    advanced_drills_completed = Column(Integer, default=0)
    # ✅ NEW: Mental training metrics
    mental_training_sessions = Column(Integer, default=0)
    total_mental_training_minutes = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="progress_history")

class SavedFilter(Base):
    __tablename__ = "saved_filters"

    id = Column(Integer, primary_key=True, index=True)  # This is the backend_id
    client_id = Column(String, unique=True, index=True)  # This stores the client's UUID
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    saved_time = Column(String, nullable=True)
    saved_equipment = Column(ARRAY(String))
    saved_training_style = Column(String, nullable=True)
    saved_location = Column(String, nullable=True)
    saved_difficulty = Column(String, nullable=True)
    
    # Relationship - using back_populates to match User model
    user = relationship("User", back_populates="saved_filters")

# Pydantic models for SavedFilter
class SavedFilterBase(BaseModel):
    id: str  # Client UUID
    backend_id: Optional[int] = None  # Backend ID if available
    name: str
    saved_time: Optional[str] = None
    saved_equipment: List[str]
    saved_training_style: Optional[str] = None
    saved_location: Optional[str] = None
    saved_difficulty: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        extra='ignore'  # Ignore any extra fields
    )

class SavedFilterCreate(BaseModel):
    saved_filters: List[SavedFilterBase]  # Match the frontend array structure

class SavedFilterUpdate(BaseModel):
    name: Optional[str] = None
    saved_equipment: Optional[List[str]] = None
    saved_training_style: Optional[str] = None
    saved_location: Optional[str] = None
    saved_difficulty: Optional[str] = None

class SavedFilterResponse(BaseModel):
    id: str  # Client UUID
    backend_id: int  # Backend ID
    name: str
    saved_time: Optional[str] = None
    saved_equipment: List[str]
    saved_training_style: Optional[str] = None
    saved_location: Optional[str] = None
    saved_difficulty: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class EmailUpdate(BaseModel):
    email: str

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

class UsernameUpdate(BaseModel):
    username: str

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
    
class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

class AvatarUpdate(BaseModel):
    avatar_path: str
    avatar_background_color: str  # Hex color code (e.g., "#FF5733")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

# Forgot Password Models
class ForgotPasswordRequest(BaseModel):
    email: str
    model_config = ConfigDict(from_attributes=True)

class ResetPasswordCodeVerification(BaseModel):
    email: str
    code: str
    model_config = ConfigDict(from_attributes=True)

class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str
    model_config = ConfigDict(from_attributes=True)

class ForgotPasswordResponse(BaseModel):
    message: str
    success: bool
    model_config = ConfigDict(from_attributes=True)

# Add this after your existing models
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    is_revoked = Column(Boolean, default=False)

    user = relationship("User", back_populates="refresh_tokens")


class PasswordResetCode(Base):
    __tablename__ = "password_reset_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    code = Column(String, index=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    is_used = Column(Boolean, default=False)

    user = relationship("User", back_populates="password_reset_codes")


class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    new_email = Column(String, index=True)  # The new email address being verified
    code = Column(String, index=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    is_used = Column(Boolean, default=False)

    user = relationship("User", back_populates="email_verification_codes")


# Email Verification Request/Response Models
class EmailVerificationRequest(BaseModel):
    new_email: str
    model_config = ConfigDict(from_attributes=True)


class EmailVerificationCodeRequest(BaseModel):
    new_email: str
    code: str
    model_config = ConfigDict(from_attributes=True)


class EmailVerificationResponse(BaseModel):
    message: str
    success: bool
    model_config = ConfigDict(from_attributes=True)


# *** MENTAL TRAINING PYDANTIC MODELS ***

class MentalTrainingQuoteResponse(BaseModel):
    id: int
    content: str
    author: str
    type: str
    display_duration: int

    model_config = ConfigDict(from_attributes=True)


# *** LEADERBOARD PYDANTIC MODELS ***
class LeaderboardEntry(BaseModel):
    """Individual leaderboard entry"""
    id: int
    username: str
    points: int
    sessions_completed: int
    rank: int
    avatar_path: Optional[str] = None
    avatar_background_color: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WorldLeaderboardResponse(BaseModel):
    """World leaderboard response with top 50 and user rank"""
    top_50: List[LeaderboardEntry]
    user_rank: LeaderboardEntry

    model_config = ConfigDict(from_attributes=True)
