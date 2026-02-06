from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import User, EmailUpdate, UsernameUpdate, PasswordUpdate, AvatarUpdate
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
        "email": current_user.email,
        "username": current_user.username,
        "avatar_path": current_user.avatar_path,
        "avatar_background_color": current_user.avatar_background_color
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

# Update user username
@router.put("/api/user/update-username")
async def update_username(
    username_update: UsernameUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user username"""
    try:
        # Check if username is already taken by another user
        if username_update.username != current_user.username:
            existing_user = db.query(User).filter(User.username == username_update.username).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
            current_user.username = username_update.username
        
        db.commit()
        db.refresh(current_user)
        
        return {
            "message": "Username updated successfully",
            "username": current_user.username
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update username: {str(e)}")

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
        # Delete all user's data (you might want to add more cascading deletes)
        db.delete(current_user)
        db.commit()
        return {"message": "Account deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(e)}") 

# Lookup user id by username
@router.get("/api/user/lookup/{username}")
async def lookup_user_id(
    username: str,
    db: Session = Depends(get_db)
):
    """Lookup user id by username"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {
        "user_id": user.id,
        "username": user.username,
        "avatar_path": user.avatar_path,
        "avatar_background_color": user.avatar_background_color
    }

# Update user avatar and background color
@router.put("/api/user/update-avatar")
async def update_avatar(
    avatar_update: AvatarUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user avatar path and background color"""
    try:
        # Validate hex color format (optional but recommended)
        hex_color = avatar_update.avatar_background_color.strip()
        if hex_color.startswith('#'):
            if len(hex_color) != 7:  # #RRGGBB format
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid hex color format. Expected format: #RRGGBB"
                )
        elif len(hex_color) == 6:
            # Add # if missing
            hex_color = f"#{hex_color}"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid hex color format. Expected format: #RRGGBB or RRGGBB"
            )
        
        # Update avatar fields
        current_user.avatar_path = avatar_update.avatar_path
        current_user.avatar_background_color = hex_color
        
        db.commit()
        db.refresh(current_user)
        
        return {
            "message": "Avatar updated successfully",
            "avatar_path": current_user.avatar_path,
            "avatar_background_color": current_user.avatar_background_color
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update avatar: {str(e)}")