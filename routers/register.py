"""
register.py
Endpoint that takes in user information and registers a new user with a hashed password
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import User, PlayerInfo
from db import get_db
from config import pwd_context


router = APIRouter()

def hash_password(password: str) -> str:
    """
    Hash a password using the pwd_context
    """
    return pwd_context.hash(password)

@router.post("/register/")
def register(player_info: PlayerInfo, db: Session = Depends(get_db)):
    """
    Register a new user and return a message if the user is already registered
    """
    existing_user = db.query(User).filter(User.email == player_info.email).first()
    
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed_password = hash_password(player_info.password)

    new_user = User(
        first_name=player_info.first_name,
        last_name=player_info.last_name,
        age=player_info.age,
        position=player_info.position,
        email=player_info.email,
        hashed_password=hashed_password,
        player_details=player_info.dict()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully", "user_id": new_user.id}
