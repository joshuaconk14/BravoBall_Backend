"""
auth.py
Securely retrieves the current user of the conversation session from the JWT token
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from db import get_db
from models import User
from datetime import datetime, timedelta
from config import UserAuth

# UserAuth variables from config.py
SECRET_KEY = UserAuth.SECRET_KEY
ALGORITHM = UserAuth.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# class that sets up Oauth2 password flow, extracts access token from request
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Create an access token for a user
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Get the current user from the JWT token (to login?, delete account, etc.)
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        #401 unathorized error
        status_code=status.HTTP_401_UNAUTHORIZED, ########
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
        # TODO is returning user like this safe?
        return user
    
    except JWTError:
        raise credentials_exception