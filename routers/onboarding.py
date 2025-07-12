from fastapi import FastAPI, HTTPException, APIRouter, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, List
from db import get_db
from models import OnboardingData, User, SessionPreferences, ProgressHistory, DrillGroup
from auth import create_access_token, create_refresh_token
from config import UserAuth
import logging
from services.session_generator import SessionGenerator
from utils.skill_mapper import map_frontend_to_backend, format_skills_for_session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# hashing the password
pwd_context = UserAuth.pwd_context
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Helper function to format session for frontend
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

@router.post("/api/onboarding")
async def create_onboarding(player_info: OnboardingData, db: Session = Depends(get_db)):
    # Log received data for debugging
    logger.info(f"Received onboarding data: {player_info}")
    
    # queries through the db to find user
    existing_user = db.query(User).filter(User.email == player_info.email).first()

    # if user already exists, raise an error
    if existing_user:
        logger.warning(f"Email already registered: {player_info.email}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    # hash the password
    hashed_password = hash_password(player_info.password)

    try:
        # connects pydantic onboarding data model to the User table
        user = User(
            # Registration / User ID
            email=player_info.email,
            hashed_password=hashed_password,

            # Onboarding - handle null values with defaults
            primary_goal=player_info.primaryGoal,
            biggest_challenge=player_info.biggestChallenge or [],
            training_experience=player_info.trainingExperience,
            position=player_info.position,
            playstyle=player_info.playstyle or [],
            age_range=player_info.ageRange,
            strengths=player_info.strengths or [],
            areas_to_improve=player_info.areasToImprove or [],
            training_location=player_info.trainingLocation or [],
            available_equipment=player_info.availableEquipment or ["ball"],
            daily_training_time=player_info.dailyTrainingTime or "30",
            weekly_training_days=player_info.weeklyTrainingDays or "moderate",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # ✅ ENHANCED: Create session preferences with proper skill mapping
        preferences = None
        try:
            # Map training experience to difficulty
            difficulty_map = {
                "Beginner": "beginner",
                "Intermediate": "intermediate", 
                "Advanced": "advanced",
                "Professional": "advanced"
            }
            
            # Map training style
            style_map = {
                "Beginner": "medium_intensity",
                "Intermediate": "medium_intensity",
                "Advanced": "high_intensity",
                "Professional": "high_intensity"
            }
            
            # Default duration (30 minutes if not specified)
            duration = 30
            if player_info.dailyTrainingTime:
                try:
                    duration = int(player_info.dailyTrainingTime)
                except ValueError:
                    # Handle case where dailyTrainingTime is not a number
                    if player_info.dailyTrainingTime == "15":
                        duration = 15
                    elif player_info.dailyTrainingTime == "30":
                        duration = 30
                    elif player_info.dailyTrainingTime == "45":
                        duration = 45
                    elif player_info.dailyTrainingTime == "60":
                        duration = 60
                    elif player_info.dailyTrainingTime == "90":
                        duration = 90
                    elif player_info.dailyTrainingTime == "120":
                        duration = 120

            # ✅ ENHANCED: Properly map frontend skills to backend format
            areas_to_improve = player_info.areasToImprove or []
            if areas_to_improve:
                # Map main skill categories to representative sub-skills
                skill_to_subskills_map = {
                    "Passing": ["Short passing", "Long passing"],
                    "Dribbling": ["Close control", "1v1 moves"], 
                    "Shooting": ["Power shots", "Finesse shots"],
                    "First touch": ["Ground control", "Touch and move"],
                    "First Touch": ["Ground control", "Touch and move"],  # Handle both cases
                    "Defending": ["Tackling", "Positioning"],
                    "Fitness": ["Speed", "Agility"]
                }
                
                # Convert main skills to specific sub-skills
                sub_skills_to_map = []
                for main_skill in areas_to_improve:
                    if main_skill in skill_to_subskills_map:
                        # Add the first two sub-skills from each category
                        sub_skills_to_map.extend(skill_to_subskills_map[main_skill])
                    else:
                        # If it's already a sub-skill, add it directly
                        sub_skills_to_map.append(main_skill)
                
                logger.info(f"Mapping skills: {areas_to_improve} -> {sub_skills_to_map}")
                
                # Convert frontend skills to backend format
                backend_skills = map_frontend_to_backend(set(sub_skills_to_map))
                # Format skills for session preferences
                formatted_skills = format_skills_for_session(backend_skills)
            else:
                formatted_skills = []
            
            logger.info(f"Final formatted skills for session: {formatted_skills}")
            
            # Create session preferences
            preferences = SessionPreferences(
                user_id=user.id,
                duration=duration,
                available_equipment=player_info.availableEquipment or ["ball"],
                training_style=style_map.get(player_info.trainingExperience, "medium_intensity"),
                training_location=player_info.trainingLocation[0] if isinstance(player_info.trainingLocation, list) and player_info.trainingLocation else "full_field",
                difficulty=difficulty_map.get(player_info.trainingExperience, "beginner"),
                target_skills=formatted_skills  # ✅ Use properly formatted skills
            )
            
            db.add(preferences)
            db.commit()
            db.refresh(preferences)
            logger.info(f"Created session preferences for user: {user.email}")
        except Exception as e:
            logger.error(f"Error creating session preferences: {str(e)}")
            # Continue even if preferences creation fails

        # ✅ NEW: Initialize user progress history
        try:
            progress_history = ProgressHistory(
                user_id=user.id,
                current_streak=0,
                previous_streak=0,
                highest_streak=0,
                completed_sessions_count=0
            )
            db.add(progress_history)
            db.commit()
            db.refresh(progress_history)
            logger.info(f"Created progress history for user: {user.email}")
        except Exception as e:
            logger.error(f"Error creating progress history: {str(e)}")
            # Continue even if progress creation fails

        # ✅ NEW: Initialize liked drills group
        try:
            liked_drills_group = DrillGroup(
                user_id=user.id,
                name="Liked Drills",
                description="Your favorite drills",
                is_liked_group=True
            )
            db.add(liked_drills_group)
            db.commit()
            db.refresh(liked_drills_group)
            logger.info(f"Created liked drills group for user: {user.email}")
        except Exception as e:
            logger.error(f"Error creating liked drills group: {str(e)}")
            # Continue even if drill group creation fails

        # Create access token after user is created, made for specific user
        access_token = create_access_token(
            data={
                "sub": user.email,
                "user_id": user.id
            }
        )
        refresh_token = create_refresh_token(user.id, db)
        
        logger.info(f"User created successfully: {user.email}")
        
        # ✅ ENHANCED: Generate initial training session if preferences were created successfully
        initial_session = None
        if preferences:
            try:
                # Generate session
                session_generator = SessionGenerator(db)
                session = await session_generator.generate_session(preferences)
                
                # Format response for frontend
                initial_session = format_session_for_frontend(session)
                logger.info(f"Generated initial training session for user: {user.email}")
                logger.info(f"Session contains {len(initial_session.get('drills', []))} drills")
            except Exception as e:
                logger.error(f"Error generating initial session: {str(e)}")
                # Continue even if session generation fails
        
        # ✅ ENHANCED: Return comprehensive response with session data
        response = {
            "status": "success",
            "message": "Onboarding completed successfully",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "email": user.email,  # ✅ Include email for frontend
            "user_id": user.id
        }
        
        # Add initial session to response if available
        if initial_session:
            response["initial_session"] = initial_session
            response["message"] = f"Onboarding completed successfully with {len(initial_session.get('drills', []))} drills generated"
        
        return response
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        db.rollback()  # ✅ Add rollback on error
        raise HTTPException(status_code=500, detail=str(e))

# Add a debug endpoint to see what data is being received
@router.post("/api/debug/onboarding")
async def debug_onboarding(data: dict):
    """Debug endpoint to see what data is being received from the frontend"""
    logger.info(f"Debug endpoint received: {data}")
    return {
        "received_data": data,
        "data_types": {k: type(v).__name__ for k, v in data.items()}
    }