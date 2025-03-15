from fastapi import FastAPI, HTTPException, APIRouter, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime
from db import get_db
from models import OnboardingData, User
from auth import create_access_token
from config import UserAuth
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# hashing the password
pwd_context = UserAuth.pwd_context
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


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

        # Create access token after user is created, made for specific user
        # create_access_token from auth.py
        access_token = create_access_token(
            data={
                "sub": user.email,
                "user_id": user.id
            }
        )
        
        logger.info(f"User created successfully: {user.email}")
        
        # returned to frontend for client to store in UserDefaults local storage
        return {
            "status": "success",
            "message": "Onboarding completed successfully",
            "access_token": access_token,
            "token_type": "Bearer"
        }
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