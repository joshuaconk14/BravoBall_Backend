from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import User, UserUpdate
from db import get_db
from auth import get_current_user
from typing import Optional

router = APIRouter()

# Get user profile information
@router.get("/api/user/")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user profile information"""
    return {
        "firstName": current_user.first_name,
        "lastName": current_user.last_name,
        "email": current_user.email
    }

# Update user profile information
@router.put("/api/user/update")
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile information"""
    try:
        # Update only provided fields
        if user_update.first_name is not None:
            current_user.first_name = user_update.first_name
        if user_update.last_name is not None:
            current_user.last_name = user_update.last_name
        if user_update.email is not None:
            current_user.email = user_update.email
        
        db.commit()
        db.refresh(current_user)
        
        return {
            "message": "Profile updated successfully",
            "firstName": current_user.first_name,
            "lastName": current_user.last_name,
            "email": current_user.email
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")

# Delete user account and all associated data
@router.delete("/api/profile/")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete user account and all associated data"""
    try:
        # Delete all user's data (you might want to add more cascading deletes)
        db.delete(current_user)
        db.commit()
        return {"message": "Account deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(e)}") 