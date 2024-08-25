"""
generate_tutorial.py
Endpoint listening for POST requests from frontend, handles user questions and uses Runnable from
memory_store.py to communicate with Llama3, while integrating with a PostgreSQL database
"""

from memory_store import with_message_history
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from models import ChatbotRequest, User, ChatHistory
from db import get_db
from langchain_core.messages import HumanMessage
import uuid
from datetime import datetime

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

@router.get('/chat_history/{user_id}')
async def get_chat_history(user_id: int, db: Session = Depends(get_db)):
    '''
    This function retrieves the chat history for a specific user
    '''
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chat_history = db.query(ChatHistory).filter(ChatHistory.user_id == user_id).order_by(ChatHistory.timestamp).all()
    return {"chat_history": [{"message": ch.message, "timestamp": ch.timestamp, "is_user": ch.is_user} for ch in chat_history]}

@router.post('/create_user/')
async def create_user(username: str, email: str, password: str, db: Session = Depends(get_db)):
    '''
    This function creates a new user in the database
    '''
    existing_user = db.query(User).filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    new_user = User(username=username, email=email, hashed_password=password)  # In production, hash the password!
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"user_id": new_user.id, "username": new_user.username}

@router.put('/update_player_details/{user_id}')
async def update_player_details(user_id: int, player_details: dict, db: Session = Depends(get_db)):
    '''
    This function updates the player details for a specific user
    '''
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.player_details = player_details
    db.commit()
    return {"message": "Player details updated successfully"}