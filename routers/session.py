from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from models import User, SessionPreferences, OnboardingData, SessionResponse, DrillResponse
from db import get_db
from auth import get_current_user
from services.session_generator import SessionGenerator
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/api/session/generate", response_model=SessionResponse)
async def generate_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a training session based on user's current preferences"""
    try:
        # Get user's preferences
        preferences = db.query(SessionPreferences).filter(SessionPreferences.user_id == current_user.id).first()
        
        if not preferences:
            # Create default preferences if none exist
            preferences = create_default_preferences(db, current_user)
        
        # Generate session
        session_generator = SessionGenerator(db)
        session = await session_generator.generate_session(preferences)
        
        return format_session_for_frontend(session)
    except Exception as e:
        logger.error(f"Error generating session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/session/preferences")
async def get_session_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the user's current session preferences"""
    try:
        # Check if user has session preferences
        preferences = db.query(SessionPreferences).filter(SessionPreferences.user_id == current_user.id).first()
        
        if not preferences:
            # Return default preferences
            return {
                "duration": 30,
                "available_equipment": current_user.available_equipment or [],
                "training_style": "medium_intensity",
                "training_location": current_user.training_location[0] if current_user.training_location else "full_field",
                "difficulty": current_user.training_experience or "beginner",
                "target_skills": current_user.areas_to_improve or []
            }
        
        return {
            "duration": preferences.duration,
            "available_equipment": preferences.available_equipment,
            "training_style": preferences.training_style,
            "training_location": preferences.training_location,
            "difficulty": preferences.difficulty,
            "target_skills": preferences.target_skills
        }
    except Exception as e:
        logger.error(f"Error getting session preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/session/preferences")
async def update_session_preferences(
    preferences: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the user's session preferences and generate a new session"""
    try:
        # Check if user has session preferences
        existing_prefs = db.query(SessionPreferences).filter(SessionPreferences.user_id == current_user.id).first()
        
        if not existing_prefs:
            # Create new preferences
            new_prefs = SessionPreferences(
                user_id=current_user.id,
                duration=preferences.get("duration", 30),
                available_equipment=preferences.get("available_equipment", []),
                training_style=preferences.get("training_style", "medium_intensity"),
                training_location=preferences.get("training_location", "full_field"),
                difficulty=preferences.get("difficulty", "beginner"),
                target_skills=preferences.get("target_skills", [])
            )
            db.add(new_prefs)
            db.commit()
            db.refresh(new_prefs)
            preferences_to_use = new_prefs
            message = "Session preferences created successfully"
        else:
            # Update existing preferences - use None for empty values
            existing_prefs.duration = preferences.get("duration")
            existing_prefs.available_equipment = preferences.get("available_equipment")
            existing_prefs.training_style = preferences.get("training_style")
            existing_prefs.training_location = preferences.get("training_location")
            existing_prefs.difficulty = preferences.get("difficulty")
            
            # Handle target_skills update
            target_skills = preferences.get("target_skills")
            if target_skills is not None:  # Only update if target_skills is provided
                # Ensure target_skills is a list of dictionaries with the correct structure
                formatted_skills = []
                for skill in target_skills:
                    if isinstance(skill, dict) and "category" in skill and "sub_skills" in skill:
                        formatted_skills.append({
                            "category": skill["category"],
                            "sub_skills": skill["sub_skills"] if isinstance(skill["sub_skills"], list) else [skill["sub_skills"]]
                        })
                existing_prefs.target_skills = formatted_skills
            else:
                existing_prefs.target_skills = []  # Set to empty list if None is provided
            
        db.commit()
        db.refresh(existing_prefs)
        preferences_to_use = existing_prefs
        message = "Session preferences updated successfully"
        
        # Generate new session with updated preferences
        session_generator = SessionGenerator(db)
        session = await session_generator.generate_session(preferences_to_use)
        
        if not session:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate session with updated preferences"
            )
        
        # Format the session
        formatted_session = format_session_for_frontend(session)
        
        # Return response with status, message, and session data
        return {
            "status": "success",
            "message": message,
            "data": formatted_session
        }
        
    except Exception as e:
        logger.error(f"Error updating session preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/session/generate-with-preferences", response_model=SessionResponse)
async def generate_session_with_preferences(
    preferences: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a session with custom preferences without saving them
    (for when user wants to generate a session with custom preferences in the main app home page)
    """
    try:
        # Create temporary preferences object
        temp_prefs = SessionPreferences(
            user_id=current_user.id,
            duration=preferences.get("duration", 30),
            available_equipment=preferences.get("available_equipment", []),
            training_style=preferences.get("training_style", "medium_intensity"),
            training_location=preferences.get("training_location", "full_field"),
            difficulty=preferences.get("difficulty", "beginner"),
            target_skills=preferences.get("target_skills", [])
        )
        
        # Generate session
        session_generator = SessionGenerator(db)
        session = await session_generator.generate_session(temp_prefs)
        
        return format_session_for_frontend(session)
    except Exception as e:
        logger.error(f"Error generating session with custom preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def create_default_preferences(db: Session, user: User) -> SessionPreferences:
    """Create default preferences for a user based on their onboarding data"""
    try:
        # Map training experience to difficulty
        difficulty_map = {
            "beginner": "beginner",
            "intermediate": "intermediate", 
            "advanced": "advanced",
            "professional": "advanced"
        }
        
        # Map training style
        style_map = {
            "beginner": "medium_intensity",
            "intermediate": "medium_intensity",
            "advanced": "high_intensity",
            "professional": "high_intensity"
        }
        
        # Default duration (30 minutes if not specified)
        duration = 30
        if user.daily_training_time:
            try:
                duration = int(user.daily_training_time)
            except ValueError:
                # Handle case where daily_training_time is not a number
                if user.daily_training_time == "15":
                    duration = 15
                elif user.daily_training_time == "30":
                    duration = 30
                elif user.daily_training_time == "45":
                    duration = 45
                elif user.daily_training_time == "60":
                    duration = 60
                elif user.daily_training_time == "90":
                    duration = 90
                elif user.daily_training_time == "120":
                    duration = 120
        
        # Create session preferences
        preferences = SessionPreferences(
            user_id=user.id,
            duration=duration,
            available_equipment=user.available_equipment or [],
            training_style=style_map.get(user.training_experience, "medium_intensity"),
            training_location=user.training_location[0] if isinstance(user.training_location, list) and user.training_location else "full_field",
            difficulty=difficulty_map.get(user.training_experience, "beginner"),
            target_skills=user.areas_to_improve or []
        )
        
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
        return preferences
    except Exception as e:
        logger.error(f"Error creating default preferences: {str(e)}")
        db.rollback()
        raise

def format_session_for_frontend(session) -> Dict[str, Any]:
    """Format training session for frontend consumption"""
    drills = []
    
    # Handle case where session has no drills
    if not hasattr(session, 'drills') or not session.drills:
        return {
            "session_id": session.id if hasattr(session, "id") else None,
            "total_duration": 0,
            "focus_areas": session.focus_areas if hasattr(session, "focus_areas") and session.focus_areas else [],
            "drills": []
        }
    
    for drill in session.drills:
        # Get adjusted_duration or fall back to duration or default
        duration = getattr(drill, "adjusted_duration", None)
        if duration is None:
            duration = drill.duration if drill.duration is not None else 10  # Default to 10 minutes
            
        # Get primary skill
        primary_skill = None
        if hasattr(drill, 'skill_focus'):
            primary_skill = next((skill for skill in drill.skill_focus if skill.is_primary), None)
            
        drill_data = {
            "id": drill.id,
            "title": drill.title,
            "description": drill.description,
            "duration": duration,
            "intensity": drill.intensity,
            "difficulty": drill.difficulty,
            "equipment": drill.equipment,
            "suitable_locations": drill.suitable_locations,
            "instructions": drill.instructions,
            "tips": drill.tips,
            "type": drill.type,
            "sets": drill.sets,
            "reps": drill.reps,
            "rest": drill.rest,
            "training_styles": drill.training_styles or [],
            "primary_skill": {
                "category": primary_skill.category if primary_skill else "general",
                "sub_skill": primary_skill.sub_skill if primary_skill else "general"
            }
        }
        drills.append(drill_data)

    # Add this new code here, just before the return statement
    focus_areas = []
    if hasattr(session, "focus_areas") and session.focus_areas:
        for area in session.focus_areas:
            if isinstance(area, dict) and "sub_skills" in area:
                focus_areas.extend(area["sub_skills"])
            elif isinstance(area, str):
                focus_areas.append(area)
    
    return {
        "session_id": session.id if hasattr(session, "id") else None,
        "total_duration": session.total_duration if hasattr(session, "total_duration") else sum(d["duration"] for d in drills),
        "focus_areas": focus_areas,
        "drills": drills
    }