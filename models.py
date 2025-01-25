"""
models.py
This defines all models used in chatbot app
"""

from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from db import Base
from enum import Enum
from sqlalchemy.sql import func


class LoginRequest(BaseModel):
    email: str
    password: str   

class UserInfoDisplay(BaseModel):
    email: str
    first_name: str 
    last_name: str

    class Config:
        orm_mode = True

# User model for PostgreSQL users data table
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    hashed_password = Column(String)
    age = Column(String)
    level = Column(String)
    position = Column(String)
    # player_details = Column(JSON)
    playstyle_representatives = Column(JSON)
    strengths = Column(JSON)
    weaknesses = Column(JSON)
    has_team = Column(Boolean, default=False)
    primary_goal = Column(String)
    timeline = Column(String)
    skill_level = Column(String)
    training_days = Column(JSON)
    available_equipment = Column(JSON)
    session_preferences = relationship("SessionPreferences", back_populates="user", uselist=False)

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
    FIELD_WITH_GOALS = "At a soccer field with goals"
    HOME = "At home (backyard or indoors)"
    PARK = "At a park or open field"
    INDOOR_COURT = "At a gym or indoor court"

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

# Updated OnboardingData model
class OnboardingData(BaseModel):
    primary_goal: PrimaryGoal
    main_challenge: Challenge
    experience_level: ExperienceLevel
    position: Position
    playstyle_representative: str
    age_range: AgeRange
    strengths: List[Skill]
    areas_to_improve: List[Skill]
    training_location: TrainingLocation
    available_equipment: List[Equipment]
    daily_training_time: TrainingDuration
    weekly_training_days: TrainingFrequency

# *** SESSION MODELS ***``

class DrillCategory(Base):
    __tablename__ = "drill_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)

class TrainingStyle(str, Enum):
    MEDIUM_INTENSITY = "medium_intensity"
    HIGH_INTENSITY = "high_intensity"
    GAME_PREP = "game_prep"
    GAME_RECOVERY = "game_recovery"
    REST_DAY = "rest_day"

class Location(str, Enum):
    INDOOR_COURT = "INDOOR_COURT"
    SMALL_FIELD = "SMALL_FIELD"
    FIELD_WITH_GOALS = "FIELD_WITH_GOALS"
    HOME = "HOME"
    GYM = "GYM"

class Difficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class DrillType(str, Enum):
    TIME_BASED = "time_based"  # e.g., "Perform for 2 minutes"
    REP_BASED = "rep_based"    # e.g., "Do 10 shots"
    SET_BASED = "set_based"    # e.g., "3 sets of 5 reps"
    CONTINUOUS = "continuous"   # e.g., "Until successful completion"

# Update the Drill model
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
    skill_focus = Column(JSON)  # Primary skills trained
    secondary_benefits = Column(JSON)  # Secondary skills improved
    
    # Content
    instructions = Column(JSON)  # List of steps
    tips = Column(JSON)  # List of coaching tips
    common_mistakes = Column(JSON)  # Things to watch out for
    variations = Column(JSON)  # Alternative versions
    progression_steps = Column(JSON)  # How to make it harder/easier
    video_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)

    category = relationship("DrillCategory", backref="drills")


    
# Add these new models after your existing models

class SessionPreferences(Base):
    __tablename__ = "session_preferences"

    id = Column(Integer, primary_key=True, index=True)
    duration = Column(Integer)  # in minutes
    available_equipment = Column(ARRAY(String))
    training_style = Column(String)
    location = Column(String)
    difficulty = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    target_skills = Column(JSON)  # List of Skill
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    user = relationship("User", back_populates="session_preferences")

    def __init__(self, duration: int, available_equipment: list, 
                 training_style: TrainingStyle, location: Location, 
                 difficulty: Difficulty, target_skills: List[str] = None):
        self.duration = duration
        self.available_equipment = available_equipment
        self.training_style = training_style.value
        self.location = location.value
        self.difficulty = difficulty.value
        self.target_skills = target_skills or []

class SessionDrill(BaseModel):
    """Represents a drill within a training session"""
    title: str
    duration: int  # in minutes
    difficulty: str
    required_equipment: List[str]
    suitable_locations: List[str]
    instructions: List[str]
    tips: List[str]

class TrainingSession(BaseModel):
    """Represents a complete training session"""
    total_duration: int
    drills: List[SessionDrill]
    focus_areas: List[str]

    class Config:
        from_attributes = True  # This allows conversion from SQLAlchemy models
    