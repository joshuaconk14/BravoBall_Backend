"""
models.py
This defines all models used in chatbot app
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any, Union
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, ARRAY, Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from db import Base
from enum import Enum
from sqlalchemy.sql import func
from datetime import datetime
from uuid import UUID

# *** AUTH MODELS ***
class LoginRequest(BaseModel):
    email: str
    password: str   

class UserInfoDisplay(BaseModel):
    email: str
    first_name: str 
    last_name: str

    model_config = ConfigDict(from_attributes=True)


# *** USER AND USER DATA MODELS ***

class User(Base):
    __tablename__ = "users"

    # Registration / User ID
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    # Onboarding 
    primary_goal = Column(String)
    biggest_challenge = Column(String)
    training_experience = Column(String)
    position = Column(String)
    playstyle = Column(String)
    age_range = Column(String)
    strengths = Column(JSON)
    areas_to_improve = Column(JSON)
    training_location = Column(JSON)
    available_equipment = Column(JSON)
    daily_training_time = Column(String)
    weekly_training_days = Column(String)
    
    
    # Relationships
    completed_sessions = relationship("CompletedSession", back_populates="user")
    drill_groups = relationship("DrillGroup", back_populates="user")
    session_preferences = relationship("SessionPreferences", back_populates="user", uselist=False)
    progress_history = relationship("ProgressHistory", back_populates="user", uselist=False)
    saved_filters = relationship("SavedFilter", back_populates="user")


class CompletedSession(Base):
    __tablename__ = "completed_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime)
    total_completed_drills = Column(Integer)
    total_drills = Column(Integer)
    
    # Store the completed drills data as JSON
    drills = Column(JSON)  # Will store array of DrillResponse data
    
    # Relationship
    user = relationship("User", back_populates="completed_sessions")



class OrderedSessionDrill(Base):
    __tablename__ = "ordered_session_drills"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("training_sessions.id"))  # Link to session
    drill_id = Column(Integer, ForeignKey("drills.id"))
    position = Column(Integer)  # Order in the session
    sets = Column(Integer, nullable=True)
    reps = Column(Integer, nullable=True)
    rest = Column(Integer, nullable=True)  # Per-session rest
    duration = Column(Integer, nullable=True)  # Per-session duration (if needed)
    is_completed = Column(Boolean, default=False)

    # Relationships
    drill = relationship("Drill")
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
    drills = relationship(
        "Drill",
        secondary="drill_group_items",
        backref="drill_groups"
    )


# New junction table for many-to-many relationship between drill groups and drills
class DrillGroupItem(Base):
    __tablename__ = "drill_group_items"
    
    id = Column(Integer, primary_key=True, index=True)
    drill_group_id = Column(Integer, ForeignKey("drill_groups.id", ondelete="CASCADE"))
    drill_id = Column(Integer, ForeignKey("drills.id", ondelete="CASCADE"))
    position = Column(Integer)  # To maintain order of drills in a group
    created_at = Column(DateTime, server_default=func.now())


# *** DRILL AND SESSION MODELS ***

class DrillCategory(Base):
    __tablename__ = "drill_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)


class DrillSkillFocus(Base):
    __tablename__ = "drill_skill_focus"
    
    id = Column(Integer, primary_key=True, index=True)
    drill_id = Column(Integer, ForeignKey("drills.id"))
    category = Column(String)  # SkillCategory enum value
    sub_skill = Column(String)  # Corresponding SubSkill enum value
    is_primary = Column(Boolean, default=True)  # Whether this is a primary or secondary skill focus


class Drill(Base):
    __tablename__ = "drills"

    id = Column(Integer, primary_key=True, index=True)
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

    # Relationships
    category = relationship("DrillCategory", backref="drills")
    skill_focus = relationship("DrillSkillFocus", backref="drill")  # Relationship to skill focus


class TrainingSession(Base):
    """Represents a complete training session"""
    __tablename__ = "training_sessions"

    id = Column(Integer, primary_key=True, index=True)
    total_duration = Column(Integer)  # in minutes
    focus_areas = Column(JSON)  # List of skill areas
    created_at = Column(DateTime, server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional user association

    # Many-to-many relationship with drills
    drills = relationship(
        "Drill",
        secondary="session_drills",
        backref="training_sessions"
    )

    user = relationship("User", backref="training_sessions")

    # Add ordered_drills relationship
    ordered_drills = relationship("OrderedSessionDrill", back_populates="session")


# Association table for many-to-many relationship between sessions and drills
session_drills = Table(
    "session_drills",
    Base.metadata,
    Column("session_id", Integer, ForeignKey("training_sessions.id")),
    Column("drill_id", Integer, ForeignKey("drills.id")),
)


# *** PYDANTIC MODELS FOR API REQUESTS/RESPONSES ***

class OnboardingData(BaseModel):
    # Optional values in onboarding with camelCase field names to match frontend
    primaryGoal: Optional[str] = None
    biggestChallenge: Optional[str] = None
    trainingExperience: Optional[str] = None
    position: Optional[str] = None
    playstyle: Optional[str] = None
    ageRange: Optional[str] = None
    strengths: Optional[List[str]] = []
    areasToImprove: Optional[List[str]] = []
    trainingLocation: Optional[List[str]] = []
    availableEquipment: Optional[List[str]] = []
    dailyTrainingTime: Optional[str] = None
    weeklyTrainingDays: Optional[str] = None

    # These should be required for registration
    firstName: str
    lastName: str
    email: str
    password: str

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
    id: int
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
    drill_ids: List[int] = []
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
    MEDIUM_INTENSITY = "medium_intensity"
    HIGH_INTENSITY = "high_intensity"
    GAME_PREP = "game_prep"
    GAME_RECOVERY = "game_recovery"
    REST_DAY = "rest_day"

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
    highest_streak = Column(Integer, default=0)
    completed_sessions_count = Column(Integer, default=0)
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

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )