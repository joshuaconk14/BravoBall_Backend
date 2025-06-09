"""
login.py
Endpoint using JWT to authenticate user upon login
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import User, LoginRequest, UserInfoDisplay, TokenResponse, RefreshTokenRequest, LoginResponse, EmailCheckRequest
from db import get_db
import jwt
from config import UserAuth
from passlib.context import CryptContext
from pydantic import BaseModel
from auth import create_access_token, create_refresh_token, verify_refresh_token, revoke_refresh_token
import logging

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

@router.post("/check-email/")
def check_email_exists(email_request: EmailCheckRequest, db: Session = Depends(get_db)):
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