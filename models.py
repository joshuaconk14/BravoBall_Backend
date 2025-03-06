"""
models.py
This defines all models used in chatbot app
"""

from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, ARRAY, Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from db import Base
from enum import Enum
from sqlalchemy.sql import func

# *** AUTH MODELS ***
class LoginRequest(BaseModel):
    email: str
    password: str

class UserInfoDisplay(BaseModel):
    email: str
    first_name: str 
    last_name: str

    model_config = ConfigDict(from_attributes=True)

# *** ONBOARDING ENUMS ***
class PrimaryGoal(str, Enum):
    IMPROVE_SKILL = "Improve my overall skill level"
    BEST_ON_TEAM = "Be the best player on my team"
    COLLEGE_SCOUTING = "Get scouted for college"
    GO_PRO = "Become a professional footballer"
    IMPROVE_FITNESS = "Improve fitness and conditioning"
    HAVE_FUN = "Have fun and enjoy the game"

class Challenge(str, Enum):
    LACK_OF_TIME = "Lack of time"
    LACK_OF_EQUIPMENT = "Lack of proper training equipment"
    UNSURE_FOCUS = "Not knowing what to work on"
    MOTIVATION = "Staying motivated"
    INJURY = "Recovering from injury"
    NO_TEAM = "No team or structured training"

class ExperienceLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"
    PROFESSIONAL = "Professional"

class Position(str, Enum):
    GOALKEEPER = "Goalkeeper"
    FULLBACK = "Fullback"
    CENTER_BACK = "Center-back"
    DEFENSIVE_MID = "Defensive Midfielder"
    CENTER_MID = "Center Midfielder"
    ATTACKING_MID = "Attacking Midfielder"
    WINGER = "Winger"
    STRIKER = "Striker"

class AgeRange(str, Enum):
    YOUTH = "Youth (Under 12)"
    TEEN = "Teen (13-16)"
    JUNIOR = "Junior (17-19)"
    ADULT = "Adult (20-29)"
    SENIOR = "Senior (30+)"

class Skill(str, Enum):
    PASSING = "Passing"
    DRIBBLING = "Dribbling"
    SHOOTING = "Shooting"
    DEFENDING = "Defending"
    FIRST_TOUCH = "First touch"
    FITNESS = "Fitness"

class TrainingLocation(str, Enum):
    FULL_FIELD = "Full-Size 11v11 Field"
    SMALL_FIELD = "Medium-Sized Grass/Turf Field"
    INDOOR_COURT = "Indoor Court (Futsal/Basketball)"
    BACKYARD = "Backyard/Small Outdoor Space"
    SMALL_ROOM = "Small Indoor Room (Living Room/Hotel)"

class Equipment(str, Enum):
    BALL = "BALL"
    CONES = "CONES"
    WALL = "WALL"
    GOALS = "GOALS"

class TrainingDuration(int, Enum):
    MINS_15 = 15
    MINS_30 = 30
    MINS_45 = 45
    MINS_60 = 60
    MINS_90 = 90
    MINS_120 = 120

class TrainingFrequency(str, Enum):
    LIGHT = "2-3 days (light schedule)"
    MODERATE = "4-5 days (moderate schedule)"
    INTENSE = "6-7 days (intense schedule)"

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

# *** USER MODELS ***
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
    
    
    # Relationship
    session_preferences = relationship("SessionPreferences", back_populates="user", uselist=False)

    
class OnboardingData(BaseModel):
    primaryGoal: str
    biggestChallenge: str
    trainingExperience: str
    position: str
    playstyle: str
    ageRange: str
    strengths: List[str]
    areasToImprove: List[str]
    trainingLocation: List[str]
    availableEquipment: List[str]
    dailyTrainingTime: str
    weeklyTrainingDays: str
    firstName: str
    lastName: str
    email: str
    password: str

    model_config = ConfigDict(from_attributes=True)

# *** DRILL MODELS ***

class DrillCategory(Base):
    __tablename__ = "drill_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)

class DrillType(str, Enum):
    TIME_BASED = "time_based"  # e.g., "Perform for 2 minutes"
    REP_BASED = "rep_based"    # e.g., "Do 10 shots"
    SET_BASED = "set_based"    # e.g., "3 sets of 5 reps"
    CONTINUOUS = "continuous"   # e.g., "Until successful completion"

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
    duration = Column(Integer)  # in minutes
    intensity_level = Column(String)  # high, medium
    suitable_training_styles = Column(JSON)  # List of TrainingStyle
    
    # Structure
    drill_type = Column(String)  # DrillType enum
    default_sets = Column(Integer, nullable=True)
    default_reps = Column(Integer, nullable=True)
    default_duration = Column(Integer, nullable=True)  # in seconds
    rest_between_sets = Column(Integer, nullable=True)  # in seconds
    
    # Requirements
    required_equipment = Column(JSON)  # List of Equipment
    recommended_equipment = Column(JSON)  # Optional equipment
    suitable_locations = Column(JSON)  # List of Location
    min_players = Column(Integer, default=1)
    max_players = Column(Integer, nullable=True)
    
    # Technical
    difficulty = Column(String)
    skill_focus = relationship("DrillSkillFocus", backref="drill")  # Relationship to skill focus
    
    # Content
    instructions = Column(JSON)  # List of steps
    tips = Column(JSON)  # List of coaching tips
    common_mistakes = Column(JSON)  # Things to watch out for
    variations = Column(JSON)  # Alternative versions
    progression_steps = Column(JSON)  # How to make it harder/easier
    video_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)

    category = relationship("DrillCategory", backref="drills")

    
# *** SESSION MODELS ***

class SessionPreferences(Base):
    __tablename__ = "session_preferences"

    id = Column(Integer, primary_key=True, index=True)
    duration = Column(Integer)  # in minutes
    available_equipment = Column(ARRAY(String))
    training_style = Column(String)
    training_location = Column(String)
    difficulty = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    target_skills = Column(JSON)  # List of {category: str, sub_skills: List[str]}
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    user = relationship("User", back_populates="session_preferences")

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

# Association table for many-to-many relationship between sessions and drills
session_drills = Table(
    "session_drills",
    Base.metadata,
    Column("session_id", Integer, ForeignKey("training_sessions.id")),
    Column("drill_id", Integer, ForeignKey("drills.id")),
)
    