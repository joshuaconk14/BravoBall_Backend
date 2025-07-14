from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from models import User, SessionPreferences, OnboardingData, SessionResponse, DrillResponse
from db import get_db
from auth import get_current_user
from services.session_generator import SessionGenerator
from utils.skill_mapper import map_frontend_to_backend, format_skills_for_session, REVERSE_SKILL_MAP
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/api/session/preferences")
async def get_session_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the user's current session preferences"""
    try:
        # Get user's preferences
        preferences = db.query(SessionPreferences).filter(SessionPreferences.user_id == current_user.id).first()
        
        if not preferences:
            raise HTTPException(
                status_code=404,
                detail="No preferences found for this user"
            )

        
        # Format target_skills as a list of frontend display names
        target_skills = []
        if preferences.target_skills:
            for skill in preferences.target_skills:
                if isinstance(skill, dict) and "category" in skill and "sub_skills" in skill:
                    for sub_skill in skill["sub_skills"]:
                        # Convert backend skill identifier to frontend display name
                        skill_id = f"{skill['category']}-{sub_skill}"
                        if skill_id in REVERSE_SKILL_MAP:
                            target_skills.append(REVERSE_SKILL_MAP[skill_id])
                elif isinstance(skill, str):
                    if skill in REVERSE_SKILL_MAP:
                        target_skills.append(REVERSE_SKILL_MAP[skill])
        
        # Format response to match frontend expectations
        response = {
            "status": "success",
            "message": "Preferences retrieved successfully",
            "data": {
                "duration": preferences.duration,
                "available_equipment": preferences.available_equipment,
                "training_style": preferences.training_style,
                "training_location": preferences.training_location,
                "difficulty": preferences.difficulty,
                "target_skills": target_skills
            }
        }
        
        # Log the formatted response
        logger.info(f"Formatted response: {response}")
        
        return response
    except Exception as e:
        logger.error(f"Error fetching session preferences: {str(e)}")
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
        
        # Format target_skills before creating/updating preferences
        target_skills = preferences.get("target_skills", [])
        if target_skills is not None:
            # Convert frontend skills to backend format
            backend_skills = map_frontend_to_backend(set(target_skills))
            # Format skills for session preferences
            formatted_skills = format_skills_for_session(backend_skills)
            preferences["target_skills"] = formatted_skills
        else:
            preferences["target_skills"] = []
        
        if not existing_prefs:
            # Create new preferences
            new_prefs = SessionPreferences(
                user_id=current_user.id,
                duration=preferences.get("duration", 30),
                available_equipment=preferences.get("available_equipment", []),
                training_style=preferences.get("training_style", "medium_intensity"),
                training_location=preferences.get("training_location", "full_field"),
                difficulty=preferences.get("difficulty", "beginner"),
                target_skills=preferences["target_skills"]
            )
            db.add(new_prefs)
            db.commit()
            db.refresh(new_prefs)
            preferences_to_use = new_prefs
            message = "Session preferences created successfully"
        else:
            # Update existing preferences
            existing_prefs.duration = preferences.get("duration")
            existing_prefs.available_equipment = preferences.get("available_equipment")
            existing_prefs.training_style = preferences.get("training_style")
            existing_prefs.training_location = preferences.get("training_location")
            existing_prefs.difficulty = preferences.get("difficulty")
            existing_prefs.target_skills = preferences["target_skills"]
        
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
        
        return {
            "status": "success",
            "message": message,
            "data": format_session_for_frontend(session)
        }
    except Exception as e:
        logger.error(f"Error updating session preferences: {str(e)}")
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
            "beginner": "low_intensity",
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
    """Format training session for frontend consumption using OrderedSessionDrill."""
    drills = []

    # Handle case where session has no ordered drills
    if not hasattr(session, 'ordered_drills') or not session.ordered_drills:
        return {
            "session_id": session.id if hasattr(session, "id") else None,
            "total_duration": 0,
            "focus_areas": [],  # Return empty list if no drills
            "drills": []
        }

    for osd in sorted(session.ordered_drills, key=lambda x: x.position):
        drill = osd.drill
        # Merge per-session and static fields
        drill_data = {
            "uuid": str(drill.uuid),  # Use UUID as primary identifier
            "title": drill.title,
            "description": drill.description,
            "duration": osd.duration if osd.duration is not None else drill.duration,
            "intensity": drill.intensity,
            "difficulty": drill.difficulty,
            "equipment": drill.equipment,
            "suitable_locations": drill.suitable_locations,
            "instructions": drill.instructions,
            "tips": drill.tips,
            "type": drill.type,
            "sets": osd.sets if osd.sets is not None else drill.sets,
            "reps": osd.reps if osd.reps is not None else drill.reps,
            "rest": osd.rest if osd.rest is not None else drill.rest,
            "training_styles": drill.training_styles or [],
            "primary_skill": {
                "category": drill.skill_focus[0].category if drill.skill_focus else "general",
                "sub_skill": drill.skill_focus[0].sub_skill if drill.skill_focus else "general"
            },
            "video_url": drill.video_url
        }
        drills.append(drill_data)

    # Format focus areas as a list of sub-skills
    focus_areas = []
    if hasattr(session, "focus_areas") and session.focus_areas:
        for area in session.focus_areas:
            if isinstance(area, dict) and "category" in area and "sub_skills" in area:
                # Just add the sub-skills
                focus_areas.extend(area["sub_skills"])
            elif isinstance(area, str):
                focus_areas.append(area)
    
    logger.info(f"Drill video URLs: {[d.get('video_url') for d in drills]}")
    
    return {
        "session_id": session.id if hasattr(session, "id") else None,
        "total_duration": session.total_duration if hasattr(session, "total_duration") else sum(d["duration"] for d in drills),
        "focus_areas": focus_areas,
        "drills": drills
    }

# ✅ NEW: Public session generation for guest users
@router.post("/public/session/generate")
async def generate_public_session(
    session_request: dict,
    db: Session = Depends(get_db)
):
    """
    Generate a training session for guest users without requiring authentication.
    This allows guests to test the session generator functionality.
    """
    try:
        logger.info(f"Generating public session for guest user with preferences: {session_request}")
        
        # Extract preferences from request
        preferences_data = session_request.get('preferences', {})
        
        # Map training experience to difficulty if not provided
        difficulty_map = {
            "Beginner": "beginner",
            "Intermediate": "intermediate", 
            "Advanced": "advanced",
            "Professional": "advanced"
        }
        
        # Map training style
        style_map = {
            "Beginner": "low_intensity",
            "Intermediate": "medium_intensity",
            "Advanced": "high_intensity",
            "Professional": "high_intensity"
        }
        
        # Create temporary session preferences object
        duration = preferences_data.get("duration", 30)
        available_equipment = preferences_data.get("available_equipment", ["ball"])
        training_style = preferences_data.get("training_style", "medium_intensity")
        training_location = preferences_data.get("training_location", "full_field")
        difficulty = preferences_data.get("difficulty", "beginner")
        target_skills = preferences_data.get("target_skills", [])
        
        # ✅ Map frontend skills to backend format if provided
        if target_skills and isinstance(target_skills, list):
            # Convert frontend skills to backend format
            backend_skills = map_frontend_to_backend(set(target_skills))
            # Format skills for session preferences
            formatted_skills = format_skills_for_session(backend_skills)
        else:
            formatted_skills = []
        
        logger.info(f"Mapped skills for public session: {target_skills} -> {formatted_skills}")
        
        # Create a temporary SessionPreferences-like object
        class TempPreferences:
            def __init__(self):
                self.user_id = None  # No user for guest
                self.duration = duration
                self.available_equipment = available_equipment
                self.training_style = training_style
                self.training_location = training_location
                self.difficulty = difficulty
                self.target_skills = formatted_skills
        
        temp_preferences = TempPreferences()
        
        # Generate session using the session generator
        session_generator = SessionGenerator(db)
        session = await session_generator.generate_session(temp_preferences)
        
        if not session:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate session with provided preferences"
            )
        
        # Format response for frontend
        session_response = format_session_for_frontend(session)
        
        logger.info(f"Generated public session with {len(session_response.get('drills', []))} drills")
        
        return {
            "status": "success",
            "message": f"Session generated successfully with {len(session_response.get('drills', []))} drills",
            "data": session_response,
            "guest_mode": True
        }
        
    except Exception as e:
        logger.error(f"Error generating public session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate session: {str(e)}")