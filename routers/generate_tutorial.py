"""
generate_tutorial.py
Endpoint listening for POST requests from frontend, handles user questions and uses Runnable from
memory_store.py to communicate with Llama3, while integrating with a PostgreSQL database
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from datetime import datetime
import uuid

from models import ChatbotRequest, User, ChatHistory, PlayerInfo
from db import get_db
from memory_store import with_message_history
from langchain_core.messages import HumanMessage

# Initialize router for 'generate_tutorial' endpoint handler
router = APIRouter()

@router.post('/generate_tutorial/')
async def generate_tutorial(request: ChatbotRequest, db: Session = Depends(get_db)):
    '''
    This decorated function listens for POST requests made to server and returns
    a Llama3 response based on user input in ChatbotRequest, while storing the conversation in the database
    '''
    try:
        # Check if the user exists
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Generate a unique session ID for each conversation if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Session ID in config identifies the user's unique conversation when Runnable is made
        config = {"configurable": {"session_id": session_id}}
        prompt = request.prompt 

        # Store the user's message in the database
        user_message = ChatHistory(
            user_id=user.id,
            session_id=session_id,
            message=prompt,
            timestamp=datetime.utcnow(),
            is_user=True
        )
        db.add(user_message)
        db.commit()

        # Llama3 runnable invoked with user question and config
        response = await with_message_history.invoke(
            [HumanMessage(content=prompt)],
            config=config,
        )

        # Store the AI's response in the database
        ai_message = ChatHistory(
            user_id=user.id,
            session_id=session_id,
            message=response.content,
            timestamp=datetime.utcnow(),
            is_user=False
        )
        db.add(ai_message)
        db.commit()

        # Return Llama3 response as dictionary so frontend can read JSON payload
        return {"tutorial": response.content, "session_id": session_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error has occurred: {str(e)}")
    

@router.post("/register/")
async def register(player_info: PlayerInfo, db: AsyncSession = Depends(get_db)):
    # Check if the email already exists
    result = await db.execute(select(User).filter(User.email == player_info.email))
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Create new user and save to the database
    new_user = User(
        first_name=player_info.first_name,
        last_name=player_info.last_name,
        age=player_info.age,
        position=player_info.position,
        email=player_info.email,
        player_details=player_info.dict()
    )
    db.add(new_user)
    await db.commit()  # Use `await` here
    await db.refresh(new_user)  # Use `await` here
    return {"message": "User registered successfully", "user_id": new_user.id}



# @router.get("/profile_status/")
# async def profile_status(email: str, db: Session = Depends(get_db)):
#     user = db.query(User).filter(User.email == email).first()
#     if not user or not user.player_details:
#         return {"profile_completed": False}
#     return {"profile_completed": True}
