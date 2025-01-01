from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import UserProgram
from db import get_db

router = APIRouter()

@router.get("/api/program/{user_id}")
async def get_user_program(user_id: int, db: Session = Depends(get_db)):
    try:
        # Get the user's program
        user_program = db.query(UserProgram).filter(UserProgram.user_id == user_id).first()
        
        if not user_program:
            raise HTTPException(status_code=404, detail="Program not found")
            
        # Structure the response for the frontend
        program_data = user_program.program_data
        current_week = user_program.current_week
        
        return {
            "currentWeek": current_week,
            "program": {
                "weeks": program_data["weeks"],
                "difficulty": program_data["difficulty"],
                "focusAreas": program_data["focus_areas"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))