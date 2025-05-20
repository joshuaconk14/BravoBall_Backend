"""
login.py
Endpoint using JWT to authenticate user upon login
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import User, LoginRequest, UserInfoDisplay
from db import get_db
import jwt
from config import UserAuth
from passlib.context import CryptContext
from pydantic import BaseModel

SECRET_KEY = UserAuth.SECRET_KEY
ALGORITHM = UserAuth.ALGORITHM
pwd_context = UserAuth.pwd_context
    
router = APIRouter()

# Add new model for email check request
class EmailCheckRequest(BaseModel):
    email: str

def verify_password(plain_password, hashed_password):
    """
    Verify the password of a user
    """
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    """
    Create an access token for a user using JWT
    """
    to_encode = data.copy()
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/login/")
def login(login_request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login a user and return an access token if the user is valid
    """
    user = db.query(User).filter(User.email == login_request.email).first()
    
    if not user or not verify_password(login_request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Converts User model data info into JSON format so can make frontend response
    user_info_JSON = UserInfoDisplay(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name
    )

    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})

    print(f"access token: {access_token}")

    #This must match the frontend structure thats storing these values (LoginResponse)
    return {
        "access_token": access_token,
         "token_type": "bearer",
         **user_info_JSON.dict()
         }


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