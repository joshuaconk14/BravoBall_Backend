"""
login.py
Endpoint using JWT to authenticate user upon login
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from models import User, LoginRequest, UserInfoDisplay, TokenResponse, RefreshTokenRequest, LoginResponse, EmailCheckRequest, ForgotPasswordRequest, ResetPasswordRequest, ForgotPasswordResponse, RefreshToken, PasswordResetCode, ResetPasswordCodeVerification
from db import get_db
import jwt
from config import UserAuth
from passlib.context import CryptContext
from pydantic import BaseModel
from auth import create_access_token, create_refresh_token, verify_refresh_token, revoke_refresh_token
import logging
import secrets
from datetime import datetime, timedelta
from services.email_service import EmailService
import os
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECRET_KEY = UserAuth.SECRET_KEY
ALGORITHM = UserAuth.ALGORITHM
pwd_context = UserAuth.pwd_context
    
router = APIRouter()


def verify_password(plain_password, hashed_password):
    """
    Verify the password of a user
    """
    return pwd_context.verify(plain_password, hashed_password)


@router.post("/login/", response_model=LoginResponse)
def login(login_request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login a user and return access and refresh tokens with user info
    """
    user = db.query(User).filter(User.email == login_request.email).first()
    
    if not user or not verify_password(login_request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
    
    # Create refresh token
    refresh_token = create_refresh_token(user.id, db)
    
    logger.info(f"User logged in successfully: {user.email}")
    
    # Return the access token, refresh token, and user info
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        email=user.email,
    )

@router.post("/refresh/", response_model=TokenResponse)
def refresh_token(refresh_request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Get a new access token using a refresh token
    """
    try:
        # Verify the refresh token and get the user
        user = verify_refresh_token(refresh_request.refresh_token, db)
        
        # Create new access token
        access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
        
        # Create new refresh token
        new_refresh_token = create_refresh_token(user.id, db)
        
        # Revoke the old refresh token
        revoke_refresh_token(refresh_request.refresh_token, db)
        
        logger.info(f"Tokens refreshed successfully for user: {user.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
    except Exception as e:
        logger.error(f"Error refreshing tokens: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.post("/check-unique-email/")
def check_email_is_new(email_request: EmailCheckRequest, db: Session = Depends(get_db)):
    """
    Check if an email already exists in the database.
    Returns:
    - exists: boolean indicating if email exists
    - message: descriptive message about the email status
    """
    user = db.query(User).filter(User.email == email_request.email).first()
    
    return {
        "exists": user is not None,
        "message": "Email already registered" if user else "Email available"
    }

@router.post("/check-existing-email/")
def check_email_exists(email_request: EmailCheckRequest, db: Session = Depends(get_db)):
    """
    Check if an email already exists in the database.
    Returns:
    - exists: boolean indicating if email exists
    - message: descriptive message about the email status
    """
    user = db.query(User).filter(User.email == email_request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found in database"
        )
    
    return {
        "exists": True,
        "message": "Email is registered"
    }

@router.post("/forgot-password/", response_model=ForgotPasswordResponse)
def forgot_password(forgot_request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == forgot_request.email).first()
        if not user:
            return ForgotPasswordResponse(message="If the email exists, a code has been sent.", success=True)
        # Generate 6-digit code
        code = f"{random.randint(100000, 999999)}"
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        # Store code
        reset_code = PasswordResetCode(user_id=user.id, code=code, expires_at=expires_at)
        db.add(reset_code)
        db.commit()
        # Send code via email
        email_service = EmailService()
        email_service.send_password_reset_code_email(user.email, code)
        return ForgotPasswordResponse(message="If the email exists, a code has been sent.", success=True)
    except Exception as e:
        logger.error(f"Error in forgot_password: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the request.")

@router.post("/verify-reset-code/")
def verify_reset_code(request: ResetPasswordCodeVerification = Body(...), db: Session = Depends(get_db)):
    """
    Verify if a password reset code is valid for the given email.
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid code or email.")
    code_entry = db.query(PasswordResetCode).filter(
        PasswordResetCode.user_id == user.id,
        PasswordResetCode.code == request.code,
        PasswordResetCode.is_used == False,
        PasswordResetCode.expires_at > datetime.utcnow()
    ).first()
    if not code_entry:
        raise HTTPException(status_code=400, detail="Invalid or expired code.")
    return {"message": "Code is valid.", "success": True}

@router.post("/reset-password/")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid code or email.")
        # Find valid, unused code
        code_entry = db.query(PasswordResetCode).filter(
            PasswordResetCode.user_id == user.id,
            PasswordResetCode.code == request.code,
            PasswordResetCode.is_used == False,
            PasswordResetCode.expires_at > datetime.utcnow()
        ).first()
        if not code_entry:
            raise HTTPException(status_code=400, detail="Invalid or expired code.")
        # Update password
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        user.hashed_password = pwd_context.hash(request.new_password)
        db.commit()
        # Mark code as used
        code_entry.is_used = True
        db.commit()
        # Revoke all refresh tokens
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).update({"is_revoked": True})
        db.commit()
        return {"message": "Password reset successfully", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in reset_password: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while resetting the password.")