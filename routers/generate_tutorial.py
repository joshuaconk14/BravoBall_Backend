"""
generate_tutorial.py
Endpoint listening for POST requests from frontend, handles user questions and uses Runnable from
memory_store.py to communicate with Llama3, while integrating with a PostgreSQL database
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from models import ChatbotRequest, User, ChatHistory
from db import get_db
from memory_store import with_message_history
from langchain_core.messages import HumanMessage

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

