"""
auth.py
Securely retrieves the current user of the conversation session from the JWT token
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from db import get_db
from models import User, RefreshToken
from models import UserInfoDisplay
from datetime import datetime, timedelta
from config import UserAuth
import secrets

# UserAuth variables from config.py
SECRET_KEY = UserAuth.SECRET_KEY
ALGORITHM = UserAuth.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = UserAuth.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = UserAuth.REFRESH_TOKEN_EXPIRE_DAYS

# class that sets up Oauth2 password flow, extracts access token from request
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict):
    """Create a new access token"""
    # copy the date
    to_encode = data.copy()
    # set the expiration time
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # update the data with the expiration time
    to_encode.update({"exp": expire})
    # encode the data with the secret key and algorithm
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(user_id: int, db: Session) -> str:
    """Create a new refresh token and store it in the database"""
    # Generate a secure random token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Create and store the refresh token
    refresh_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    db.add(refresh_token)
    db.commit()
    
    return token

def verify_refresh_token(token: str, db: Session) -> User:
    """Verify a refresh token and return the associated user"""
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == token,
        RefreshToken.is_revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()
    
    # if the refresh token is not found, return a 401 unathorized error
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    return refresh_token.user

def revoke_refresh_token(token: str, db: Session):
    """Revoke a refresh token"""
    refresh_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if refresh_token:
        refresh_token.is_revoked = True
        db.commit()

# Get the current user from the JWT token
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        #401 unathorized error
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # decoding the JWT, checking if it's valid and not expired
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user_id = payload.get("user_id")
        if email is None or user_id is None:
            raise credentials_exception
        
        # # find the user based off the user_id given from the encoded JWT payload
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise credentials_exception
        # TODO is returning user like this safe?
        return user
    
    except JWTError:
        raise credentials_exception

    # Get the current user's display info: first name, last name, and email
def get_user_display_info(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        #401 unathorized error
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # decoding the JWT, checking if it's valid
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user_id = payload.get("user_id")
        if email is None or user_id is None:
            raise credentials_exception
        
        # # find the user based off the user_id given from the encoded JWT payload
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise credentials_exception
        
        return UserInfoDisplay(email=user.email)
    
    except JWTError:
        raise credentials_exception