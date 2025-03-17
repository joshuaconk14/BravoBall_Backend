from fastapi import FastAPI, HTTPException, APIRouter, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, List
from db import get_db
from models import OnboardingData, User, SessionPreferences
from auth import create_access_token
from config import UserAuth
import logging
from services.session_generator import SessionGenerator

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
            "rest": drill.rest
        }
        drills.append(drill_data)
    
    return {
        "session_id": session.id if hasattr(session, "id") else None,
        "total_duration": session.total_duration if hasattr(session, "total_duration") else sum(d["duration"] for d in drills),
        "focus_areas": session.focus_areas or [],
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
            first_name=player_info.firstName,
            last_name=player_info.lastName,
            email=player_info.email,
            hashed_password=hashed_password,

            # Onboarding - handle null values
            primary_goal=player_info.primaryGoal or None,
            biggest_challenge=player_info.biggestChallenge or None,
            training_experience=player_info.trainingExperience or None,
            position=player_info.position or None,
            playstyle=player_info.playstyle or None,
            age_range=player_info.ageRange or None,
            strengths=player_info.strengths or [],
            areas_to_improve=player_info.areasToImprove or [],
            training_location=player_info.trainingLocation or [],
            available_equipment=player_info.availableEquipment or [],
            daily_training_time=player_info.dailyTrainingTime or None,
            weekly_training_days=player_info.weeklyTrainingDays or None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create session preferences from onboarding data
        preferences = None
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
            
            # Create session preferences
            preferences = SessionPreferences(
                user_id=user.id,
                duration=duration,
                available_equipment=player_info.availableEquipment or [],
                training_style=style_map.get(player_info.trainingExperience, "medium_intensity"),
                training_location=player_info.trainingLocation[0] if isinstance(player_info.trainingLocation, list) and player_info.trainingLocation else "full_field",
                difficulty=difficulty_map.get(player_info.trainingExperience, "beginner"),
                target_skills=player_info.areasToImprove or []
            )
            
            db.add(preferences)
            db.commit()
            db.refresh(preferences)
            logger.info(f"Created session preferences for user: {user.email}")
        except Exception as e:
            logger.error(f"Error creating session preferences: {str(e)}")
            # Continue even if preferences creation fails

        # Create access token after user is created, made for specific user
        # create_access_token from auth.py
        access_token = create_access_token(
            data={
                "sub": user.email,
                "user_id": user.id
            }
        )
        
        logger.info(f"User created successfully: {user.email}")
        
        # Generate initial training session if preferences were created successfully
        initial_session = None
        if preferences:
            try:
                # Generate session
                session_generator = SessionGenerator(db)
                session = await session_generator.generate_session(preferences)
                
                # Format response for frontend
                initial_session = format_session_for_frontend(session)
                logger.info(f"Generated initial training session for user: {user.email}")
            except Exception as e:
                logger.error(f"Error generating initial session: {str(e)}")
                # Continue even if session generation fails
        
        # returned to frontend for client to store in UserDefaults local storage
        response = {
            "status": "success",
            "message": "Onboarding completed successfully",
            "access_token": access_token,
            "token_type": "Bearer",
            "user_id": user.id
        }
        
        # Add initial session to response if available
        if initial_session:
            response["initial_session"] = initial_session
        
        return response
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
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