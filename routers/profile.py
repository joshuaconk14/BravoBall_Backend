from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import User, EmailUpdate, PasswordUpdate, PremiumSubscription
from db import get_db
from auth import get_current_user
from passlib.context import CryptContext

router = APIRouter()

# Get user profile information
@router.get("/api/user/")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user profile information"""
    return {
        "email": current_user.email
    }

# Update user email
@router.put("/api/user/update-email")
async def update_email(
    email_update: EmailUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user email"""
    try:
        # Check if email is already taken by another user
        if email_update.email != current_user.email:
            existing_user = db.query(User).filter(User.email == email_update.email).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            current_user.email = email_update.email
        
        db.commit()
        db.refresh(current_user)
        
        return {
            "message": "Email updated successfully",
            "email": current_user.email
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update email: {str(e)}")

# Update user password
@router.put("/api/user/update-password")
async def update_password(
    password_update: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user password"""
    try:
        # Verify current password
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        if not pwd_context.verify(password_update.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )

        # Update password
        current_user.hashed_password = pwd_context.hash(password_update.new_password)
        
        db.commit()
        db.refresh(current_user)
        
        return {
            "message": "Password updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update password: {str(e)}")

# Delete user account and all associated data
@router.delete("/api/profile/")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete user account and all associated data"""
    try:
        # Delete premium subscription first
        db.query(PremiumSubscription).filter(
            PremiumSubscription.user_id == current_user.id
        ).delete()
        
        # Delete all user's data (you might want to add more cascading deletes)
        db.delete(current_user)
        db.commit()
        return {"message": "Account deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(e)}") 