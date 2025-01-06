"""
login.py
Endpoint using JWT to authenticate user upon login
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import User, LoginRequest
from db import get_db
import jwt
from config import UserAuth
from passlib.context import CryptContext

SECRET_KEY = UserAuth.SECRET_KEY
ALGORITHM = UserAuth.ALGORITHM
pwd_context = UserAuth.pwd_context
    
router = APIRouter()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login/")
def login(login_request: User, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_request.email).first()
    
    if not user or not verify_password(login_request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
    print(f"access token: {access_token}")
    return {"access_token": access_token, "token_type": "bearer"}
