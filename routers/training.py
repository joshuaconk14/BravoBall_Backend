from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from models import User, SessionPreferences
from db import get_db
from auth import get_current_user
from services.session_generator import SessionGenerator

router = APIRouter()

@router.post("/api/session/generate")
async def generate_session(
    preferences: SessionPreferences,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a training session based on user preferences and profile"""
    try:
        session_generator = SessionGenerator(db)
        session = await session_generator.generate_session(current_user, preferences)
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))