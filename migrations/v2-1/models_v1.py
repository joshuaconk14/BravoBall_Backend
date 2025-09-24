"""
V1-specific database models for migration purposes.

These models represent the actual schema of the V1 database and should be used
for all V1 database operations during migration.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, ARRAY, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class UserV1(Base):
    """V1 User model - represents the actual V1 database schema"""
    __tablename__ = 'users'
    
    # Registration / User ID
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
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
    
    # Relationships
    completed_sessions = relationship("CompletedSessionV1", back_populates="user")
    drill_groups = relationship("DrillGroupV1", back_populates="user")
    session_preferences = relationship("SessionPreferencesV1", back_populates="user", uselist=False)
    progress_history = relationship("ProgressHistoryV1", back_populates="user", uselist=False)
    saved_filters = relationship("SavedFilterV1", back_populates="user")
    refresh_tokens = relationship("RefreshTokenV1", back_populates="user")
    password_reset_codes = relationship("PasswordResetCodeV1", back_populates="user")
    training_sessions = relationship("TrainingSessionV1", back_populates="user")


class CompletedSessionV1(Base):
    """V1 Completed Session model - represents the actual V1 database schema"""
    __tablename__ = 'completed_sessions'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime)
    total_completed_drills = Column(Integer)
    total_drills = Column(Integer)
    
    # Store the completed drills data as JSON
    drills = Column(JSON)  # Will store array of DrillResponse data
    
    # Relationship
    user = relationship("UserV1", back_populates="completed_sessions")


class OrderedSessionDrillV1(Base):
    """V1 Ordered Session Drill model - represents the actual V1 database schema"""
    __tablename__ = "ordered_session_drills"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("training_sessions.id"))  # Link to session
    drill_id = Column(Integer, ForeignKey("drills.id"))
    position = Column(Integer)  # Order in the session
    sets_done = Column(Integer)
    sets = Column(Integer, nullable=True)
    reps = Column(Integer, nullable=True)
    rest = Column(Integer, nullable=True)  # Per-session rest
    duration = Column(Integer, nullable=True)  # Per-session duration (if needed)
    is_completed = Column(Boolean, default=False)

    # Relationships
    drill = relationship("DrillV1")
    session = relationship("TrainingSessionV1", back_populates="ordered_drills")


class SessionPreferencesV1(Base):
    """V1 Session Preferences model - represents the actual V1 database schema"""
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

    user = relationship("UserV1", back_populates="session_preferences")


class DrillGroupV1(Base):
    """V1 Drill Group model - represents the actual V1 database schema"""
    __tablename__ = "drill_groups"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    description = Column(String)
    is_liked_group = Column(Boolean, default=False)  # To identify if this is the "Liked Drills" group
    
    # Relationships
    user = relationship("UserV1", back_populates="drill_groups")
    drill_items = relationship("DrillGroupItemV1", back_populates="drill_group")


class DrillGroupItemV1(Base):
    """V1 Drill Group Item model - represents the actual V1 database schema"""
    __tablename__ = "drill_group_items"
    
    id = Column(Integer, primary_key=True, index=True)
    drill_group_id = Column(Integer, ForeignKey("drill_groups.id", ondelete="CASCADE"))
    drill_id = Column(Integer, ForeignKey("drills.id", ondelete="CASCADE"))
    position = Column(Integer)  # To maintain order of drills in a group
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    drill_group = relationship("DrillGroupV1", back_populates="drill_items")


class DrillCategoryV1(Base):
    """V1 Drill Category model - represents the actual V1 database schema"""
    __tablename__ = "drill_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)


class DrillSkillFocusV1(Base):
    """V1 Drill Skill Focus model - represents the actual V1 database schema"""
    __tablename__ = "drill_skill_focus"
    
    id = Column(Integer, primary_key=True, index=True)
    drill_id = Column(Integer, ForeignKey("drills.id"))
    category = Column(String)  # SkillCategory enum value
    sub_skill = Column(String)  # Corresponding SubSkill enum value
    is_primary = Column(Boolean, default=True)  # Whether this is a primary or secondary skill focus


class DrillV1(Base):
    """V1 Drill model - represents the actual V1 database schema"""
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
    category = relationship("DrillCategoryV1", backref="drills")
    skill_focus = relationship("DrillSkillFocusV1", backref="drill")  # Relationship to skill focus


class TrainingSessionV1(Base):
    """V1 Training Session model - represents the actual V1 database schema"""
    __tablename__ = "training_sessions"

    id = Column(Integer, primary_key=True, index=True)
    total_duration = Column(Integer)  # in minutes
    focus_areas = Column(JSON)  # List of skill areas
    created_at = Column(DateTime, server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional user association

    # Relationships
    user = relationship("UserV1", back_populates="training_sessions")
    ordered_drills = relationship("OrderedSessionDrillV1", back_populates="session")


class ProgressHistoryV1(Base):
    """V1 Progress History model - represents the actual V1 database schema"""
    __tablename__ = "progress_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    current_streak = Column(Integer, default=0)
    highest_streak = Column(Integer, default=0)
    completed_sessions_count = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship
    user = relationship("UserV1", back_populates="progress_history")


class SavedFilterV1(Base):
    """V1 Saved Filter model - represents the actual V1 database schema"""
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
    user = relationship("UserV1", back_populates="saved_filters")


class RefreshTokenV1(Base):
    """V1 Refresh Token model - represents the actual V1 database schema"""
    __tablename__ = 'refresh_tokens'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("UserV1", back_populates="refresh_tokens")


class PasswordResetCodeV1(Base):
    """V1 Password Reset Code model - represents the actual V1 database schema"""
    __tablename__ = 'password_reset_codes'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    code = Column(String)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("UserV1", back_populates="password_reset_codes")


# Note: V1 doesn't have the following tables that exist in V2:
# - email_verification_codes
# - mental_training_sessions  
# - mental_training_quotes