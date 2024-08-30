from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import User, LoginRequest
from db import aget_db
import jwt
from config import SECRET_KEY, ALGORITHM, pwd_context
from passlib.context import CryptContext


router = APIRouter()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login/")
async def login(login_request: LoginRequest, db: AsyncSession = Depends(aget_db)):
    # Find user by email
    result = await db.execute(select(User).filter(User.email == login_request.email))
    user = result.scalars().first()
    
    # Check if the user exists and password matches
    if not user or not verify_password(login_request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate access token
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

