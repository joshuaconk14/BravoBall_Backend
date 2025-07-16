from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import User, MentalTrainingQuote, MentalTrainingQuoteResponse
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

