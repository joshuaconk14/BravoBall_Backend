"""
delete_account.py
Endpoint to delete user account
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import User, OrderedSessionDrill, CompletedSession, DrillGroup, SessionPreferences, ProgressHistory, SavedFilter, TrainingSession, MentalTrainingSession, CustomDrill, RefreshToken, PasswordResetCode, EmailVerificationCode, PremiumSubscription, AuditLog
from db import get_db
from auth import get_current_user

router = APIRouter()

@router.delete("/delete-account/")
async def delete_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete user account and all associated data"""
    try:
        # First find all training sessions for the user
        user_sessions = db.query(TrainingSession).filter(
            TrainingSession.user_id == current_user.id
        ).all()
        
        # Get all session IDs
        session_ids = [session.id for session in user_sessions]
        
        # Delete ordered session drills for these sessions
        if session_ids:
            db.query(OrderedSessionDrill).filter(
                OrderedSessionDrill.session_id.in_(session_ids)
            ).delete()
        
        # Delete the training sessions
        db.query(TrainingSession).filter(
            TrainingSession.user_id == current_user.id
        ).delete()

        # Delete completed sessions
        db.query(CompletedSession).filter(
            CompletedSession.user_id == current_user.id
        ).delete()

        # Delete mental training sessions
        db.query(MentalTrainingSession).filter(
            MentalTrainingSession.user_id == current_user.id
        ).delete()

        # Delete custom drills
        db.query(CustomDrill).filter(
            CustomDrill.user_id == current_user.id
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

        # Delete refresh tokens
        db.query(RefreshToken).filter(
            RefreshToken.user_id == current_user.id
        ).delete()

        # Delete password reset codes
        db.query(PasswordResetCode).filter(
            PasswordResetCode.user_id == current_user.id
        ).delete()

        # Delete email verification codes
        db.query(EmailVerificationCode).filter(
            EmailVerificationCode.user_id == current_user.id
        ).delete()

        # Delete premium subscription
        db.query(PremiumSubscription).filter(
            PremiumSubscription.user_id == current_user.id
        ).delete()

        # Delete audit logs for this user
        db.query(AuditLog).filter(
            AuditLog.user_id == current_user.id
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
