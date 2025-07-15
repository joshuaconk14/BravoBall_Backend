from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import User, MentalTrainingQuote, MentalTrainingSession, CompletedSession, MentalTrainingQuoteResponse, MentalTrainingSessionCreate, MentalTrainingSessionResponse
from db import get_db
from auth import get_current_user
import logging
from sqlalchemy import func
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/api/mental-training/quotes", response_model=List[MentalTrainingQuoteResponse])
async def get_mental_training_quotes(
    limit: int = 50,
    quote_type: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get mental training quotes for the timer display.
    Returns a randomized list of quotes to cycle through during mental training.
    """
    try:
        logger.info(f"Fetching mental training quotes for user: {current_user.email}")
        
        # Start with all quotes
        query = db.query(MentalTrainingQuote)
        
        # Filter by type if specified
        if quote_type:
            query = query.filter(MentalTrainingQuote.type == quote_type)
        
        # Get random quotes
        quotes = query.order_by(func.random()).limit(limit).all()
        
        logger.info(f"Found {len(quotes)} mental training quotes")
        
        return quotes
        
    except Exception as e:
        logger.error(f"Error fetching mental training quotes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch mental training quotes: {str(e)}")

@router.post("/api/mental-training/sessions", response_model=MentalTrainingSessionResponse)
async def create_mental_training_session(
    session_data: MentalTrainingSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record a completed mental training session.
    This counts toward the user's daily training streak.
    """
    try:
        logger.info(f"Creating mental training session for user: {current_user.email}")
        logger.info(f"Session duration: {session_data.duration_minutes} minutes")
        
        # Create new mental training session
        new_session = MentalTrainingSession(
            user_id=current_user.id,
            duration_minutes=session_data.duration_minutes,
            session_type=session_data.session_type
        )
        
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        
        logger.info(f"Mental training session created successfully with ID: {new_session.id}")
        
        # ✅ NEW: Create completed session entry for streak tracking
        completed_session = CompletedSession(
            user_id=current_user.id,
            date=new_session.created_at,  # Use the session creation time
            session_type='mental_training',
            duration_minutes=session_data.duration_minutes,
            mental_training_session_id=new_session.id,
            # Drill fields are None for mental training
            total_completed_drills=None,
            total_drills=None,
            drills=None
        )
        
        db.add(completed_session)
        db.commit()
        db.refresh(completed_session)
        
        logger.info(f"Created completed session entry for mental training session ID: {new_session.id}")
        
        return new_session
        
    except Exception as e:
        logger.error(f"Error creating mental training session: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create mental training session: {str(e)}")

@router.get("/api/mental-training/sessions", response_model=List[MentalTrainingSessionResponse])
async def get_user_mental_training_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all mental training sessions for the current user.
    Used for progress tracking and calendar display.
    """
    try:
        logger.info(f"Fetching mental training sessions for user: {current_user.email}")
        
        sessions = db.query(MentalTrainingSession).filter(
            MentalTrainingSession.user_id == current_user.id
        ).order_by(MentalTrainingSession.date.desc()).all()
        
        logger.info(f"Found {len(sessions)} mental training sessions")
        
        return sessions
        
    except Exception as e:
        logger.error(f"Error fetching mental training sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch mental training sessions: {str(e)}")

@router.get("/api/mental-training/sessions/today")
async def get_today_mental_training_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get mental training sessions completed today.
    Used for daily progress tracking.
    """
    try:
        from datetime import datetime, date
        
        today = date.today()
        sessions = db.query(MentalTrainingSession).filter(
            MentalTrainingSession.user_id == current_user.id,
            func.date(MentalTrainingSession.date) == today
        ).all()
        
        total_minutes = sum(session.duration_minutes for session in sessions)
        
        return {
            "sessions_today": len(sessions),
            "total_minutes_today": total_minutes,
            "sessions": [
                {
                    "id": session.id,
                    "duration_minutes": session.duration_minutes,
                    "session_type": session.session_type,
                    "date": session.date
                }
                for session in sessions
            ]
        }
        
    except Exception as e:
        logger.error(f"Error fetching today's mental training sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch today's mental training sessions: {str(e)}") 