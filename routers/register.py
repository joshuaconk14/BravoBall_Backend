from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import User, PlayerInfo
from db import get_db
from config import pwd_context


router = APIRouter()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

@router.post("/register/")
async def register(player_info: PlayerInfo, db: AsyncSession = Depends(get_db)):
    # Check if the email already exists
    result = await db.execute(select(User).filter(User.email == player_info.email))
    existing_user = result.scalars().first()
    
    hashed_password = hash_password(player_info.password)

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Create new user and save to the database
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
    await db.commit()  # Use `await` here
    await db.refresh(new_user)  # Use `await` here
    return {"message": "User registered successfully", "user_id": new_user.id}
