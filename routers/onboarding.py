from fastapi import FastAPI, HTTPException, APIRouter, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime
from db import get_db
from models import OnboardingData, User, UserProgram
from auth import create_access_token
from config import UserAuth

router = APIRouter()
# program_generator = ProgramGenerator()

# hashing the password
pwd_context = UserAuth.pwd_context
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


@router.post("/api/onboarding")
async def create_onboarding(player_info: OnboardingData, db: Session = Depends(get_db)):
    # queries through the db to find user
    existing_user = db.query(User).filter(User.email == player_info.email).first()

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    hashed_password = hash_password(player_info.password)

    try:
        # connects pydantic onboarding data model to the User table
        user = User(
            first_name=player_info.firstName,
            last_name=player_info.lastName,
            email=player_info.email,
            hashed_password=hashed_password,
            age = player_info.ageRange,
            position=player_info.position,
            playstyle_representatives=player_info.playstyleRepresentatives,
            strengths=player_info.strengths,
            weaknesses=player_info.weaknesses,
            has_team=player_info.hasTeam,
            primary_goal=player_info.primaryGoal,
            timeline=player_info.timeline,
            skill_level=player_info.skillLevel,
            training_days=player_info.trainingDays,
            available_equipment=player_info.availableEquipment
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
        
        # returned to frontend for client to store in UserDefaults local storage
        return {
            "status": "success",
            "message": "Onboarding completed successfully",
            "access_token": access_token,
            "token_type": "Bearer"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))