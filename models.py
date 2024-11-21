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

# Request model to be used in payload
class ChatbotRequest(BaseModel):
    # user_id: int
    prompt: str 
    session_id: str
    
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
    
    # Relationships
    goals = relationship("PlayerGoals", back_populates="user")
    strengths = relationship("PlayerStrengths", back_populates="user")
    weaknesses = relationship("PlayerWeaknesses", back_populates="user")
    style_references = relationship("PlayerStyleReferences", back_populates="user")

    # for future use
    chat_histories = relationship("ChatHistory", back_populates="user")

# ChatHistory model for PostgreSQL chat_history data table
class ChatHistory(Base):
    __tablename__ = "chat_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String, index=True)
    message = Column(JSONB)
    timestamp = Column(DateTime)
    is_user = Column(Boolean, default=True)

    user = relationship("User", back_populates="chat_histories")

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

class Drill(BaseModel):
    title: str
    description: str
    duration: int
    type: str
    difficulty: str
    equipment: List[str]
    instructions: List[str]
    tips: List[str]
    video_url: str | None = None

# Database models
class UserProgram(Base):
    __tablename__ = "user_programs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    program_data = Column(JSONB)
    created_at = Column(DateTime)
    current_week = Column(Integer, default=1)
    
    user = relationship("User", back_populates="program")

# Add this to your User model
program = relationship("UserProgram", back_populates="user", uselist=False)