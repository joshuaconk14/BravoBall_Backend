"""
models.py
This defines all models used in chatbot app
"""

from pydantic import BaseModel
from typing import List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from db import Base

# Player details the user states in the frontend
class PlayerDetails(BaseModel):
    name: str
    age: int
    position: str
    
# Request model for profile creation
class PlayerInfo(BaseModel):
    first_name: str
    last_name: str
    age: int
    position: str
    # TODO put this in another class
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str   

# User model for PostgreSQL users data table
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    age = Column(Integer)
    position = Column(String)
    hashed_password = Column(String)
    player_details = Column(JSON)
    level = Column(String)
    has_team = Column(Boolean, default=False)
    primary_goal = Column(String)
    skill_level = Column(String)
    available_equipment = Column(JSON)
    
    # Only keep the relationships that we have tables for
    chat_histories = relationship("ChatHistory", back_populates="user")
    program = relationship("UserProgram", back_populates="user", uselist=False)

class OnboardingData(BaseModel):
    firstName: str
    lastName: str
    ageRange: str
    level: str
    position: str
    playstyleRepresentatives: List[str]
    strengths: List[str]
    weaknesses: List[str]
    hasTeam: bool
    primaryGoal: str
    timeline: str
    skillLevel: str
    trainingDays: List[str]
    availableEquipment: List[str]


# *** PROGRAM MODELS ***``
class Program(BaseModel):
    weeks: List["Week"]
    difficulty: str
    focus_areas: List[str]

class TrainingDay(BaseModel):
    day: str  # e.g., "Monday"
    drills: List["Drill"]
    focus: str  # Primary focus for this day
    total_duration: int

class Week(BaseModel):
    week_number: int
    theme: str
    description: str
    training_days: List[TrainingDay]  # Instead of just drills

class DrillCategory(Base):
    __tablename__ = "drill_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)

class Drill(Base):
    __tablename__ = "drills"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    category_id = Column(Integer, ForeignKey("drill_categories.id"))
    duration = Column(Integer)  # in minutes
    difficulty = Column(String)
    instructions = Column(JSON)  # List of steps
    tips = Column(JSON)  # List of coaching tips
    recommended_equipment = Column(JSON)  # List of required equipment
    recommended_positions = Column(JSON)  # List of recommended positions
    video_url = Column(String, nullable=True)
    skill_focus = Column(JSON)

    category = relationship("DrillCategory", backref="drills")

# Database models
#TODO figure out how to use this
class UserProgram(Base):
    __tablename__ = "user_programs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    program_data = Column(JSONB)
    created_at = Column(DateTime)
    current_week = Column(Integer, default=1)
    
    user = relationship("User", back_populates="program")
    