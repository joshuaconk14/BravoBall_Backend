from fastapi import FastAPI, HTTPException, APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
# from services.program_generator import ProgramGenerator
from db import get_db
from models import OnboardingData, User, UserProgram
from auth import create_access_token
from .services.drill_recommender import DrillRecommender

router = APIRouter()
# program_generator = ProgramGenerator()

@router.post("/api/onboarding")
async def create_onboarding(data: OnboardingData, db: Session = Depends(get_db)):
    try:
        # Generate a mock email using the user's name
        mock_email = "testdrills20@example.com"
        mock_password = "defaultpassword123"  # TODO use a more secure method in production
        mock_first_name = "John"
        mock_last_name = "Doe"
        mock_primary_goal = "Improve my skills"




        
        
        # TODO: implement hashed password so can get rid of register endpoint
        # TODO: make registerview uipdate onboarding data like how firstQ and secondQ are doing




        user = User(
            email=mock_email,
            hashed_password=mock_password,
            first_name=mock_first_name,
            last_name=mock_last_name,
            level=data.level,
            position=data.position,
            has_team=data.hasTeam,
            primary_goal=mock_primary_goal,
            skill_level=data.skillLevel,
            available_equipment=data.availableEquipment
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Get drill recommendations for the newly created user
        recommender = DrillRecommender(db)
        recommended_drills = recommender.get_recommendations(user)
        
        # Create access token
        access_token = create_access_token(
            data={
                "sub": mock_email,
                "user_id": user.id
            }
        )
        
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