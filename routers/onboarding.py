from fastapi import FastAPI, HTTPException, APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
# from services.program_generator import ProgramGenerator
from db import get_db
from models import OnboardingData, User, UserProgram

router = APIRouter()
# program_generator = ProgramGenerator()

@router.post("/api/onboarding")
async def create_onboarding(data: OnboardingData, db: Session = Depends(get_db)):
    try:
        # # Generate program
        # program = await program_generator.generate_program(data)
        
        # # Create user record
        # user = User(
        #     first_name=data.firstName,
        #     last_name=data.lastName,
        #     level=data.level,
        #     position=data.position,
        #     has_team=data.hasTeam,
        #     primary_goal=data.primaryGoal,
        #     skill_level=data.skillLevel
        # )
        # db.add(user)
        # db.flush()
        
        # # Create program record
        # user_program = UserProgram(
        #     user_id=user.id,
        #     program_data=program.dict(),
        #     created_at=datetime.utcnow(),
        #     current_week=1
        # )
        # db.add(user_program)
        # db.commit()
        
        return {
            "status": "success",
            "message": "Onboarding completed and program generated",
            # "program": program    
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))