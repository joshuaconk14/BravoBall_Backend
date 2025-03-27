"""
delete_account.py
Endpoint to delete user account
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import User, OrderedSessionDrill, CompletedSession, DrillGroup, SessionPreferences, ProgressHistory, SavedFilter
from db import get_db
from auth import get_current_user

router = APIRouter()

@router.delete("/delete-account/")
async def delete_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete user account and all associated data"""
    try:
        # Delete ordered session drills
        db.query(OrderedSessionDrill).filter(
            OrderedSessionDrill.user_id == current_user.id
        ).delete()

        # Delete completed sessions
        db.query(CompletedSession).filter(
            CompletedSession.user_id == current_user.id
        ).delete()

        # Delete drill groups
        db.query(DrillGroup).filter(
            DrillGroup.user_id == current_user.id
        ).delete()

        # Delete session preferences
        db.query(SessionPreferences).filter(
            SessionPreferences.user_id == current_user.id
        ).delete()

        # Delete progress history
        db.query(ProgressHistory).filter(
            ProgressHistory.user_id == current_user.id
        ).delete()

        # Delete saved filters
        db.query(SavedFilter).filter(
            SavedFilter.user_id == current_user.id
        ).delete()

        # Finally, delete the user
        db.delete(current_user)
        db.commit()

        return {"status": "success", "message": "User account and all associated data deleted successfully"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An error occurred while deleting the user account: {str(e)}"
        )
