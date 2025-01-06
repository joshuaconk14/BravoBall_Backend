from fastapi import FastAPI, HTTPException, APIRouter, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime
# from services.program_generator import ProgramGenerator
from db import get_db
from models import OnboardingData, User, UserProgram
from auth import create_access_token
from .services.drill_recommender import DrillRecommender
from config import UserAuth

router = APIRouter()
# program_generator = ProgramGenerator()

# hashing the password
pwd_context = UserAuth.pwd_context
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


@router.post("/api/onboarding")
async def create_onboarding(player_info: OnboardingData, db: Session = Depends(get_db)):
    # try:
    #     # Generate a mock email using the user's name
    #     mock_email = "testdrills20@example.com"
    #     mock_password = "defaultpassword123"  # TODO use a more secure method in production
    #     mock_first_name = "John"
    #     mock_last_name = "Doe"
    #     mock_primary_goal = "Improve my skills"

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
        
        # Get drill recommendations for the newly created user
        recommender = DrillRecommender(db)
        recommended_drills = recommender.get_recommendations(user)
        
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
            "token_type": "Bearer",
            "recommendations": [
                {
                    "id": drill.id,
                    "title": drill.title,
                    "description": drill.description,
                    "category": drill.category.name,
                    "duration": drill.duration,
                    "difficulty": drill.difficulty,
                    "recommended_equipment": drill.recommended_equipment,
                    "instructions": drill.instructions,
                    "tips": drill.tips,
                    "video_url": drill.video_url,
                    "matchScore": {
                        "skillLevelMatch": True if drill.difficulty == user.skill_level else False,
                        "equipmentAvailable": all(item in user.available_equipment for item in drill.recommended_equipment),
                        "recommendedForPosition": user.position in drill.recommended_positions if drill.recommended_positions else False,
                        "calculatedScore": round(score, 2)
                    }
                } for drill, score in recommended_drills
            ],
            "metadata": {
                "totalDrills": len(recommended_drills),
                "userSkillLevel": user.skill_level,
                "userPosition": user.position,
                "availableEquipment": user.available_equipment
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))