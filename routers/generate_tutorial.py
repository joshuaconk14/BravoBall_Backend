"""
generate_tutorial.py
Endpoint listening for POST requests from frontend, handles user questions and uses Runnable from
memory_store.py to communicate with Llama3, while integrating with a PostgreSQL database
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import exc
from datetime import datetime
import uuid
from models import ChatbotRequest, User, ChatHistory
from db import get_db
from memory_store import with_message_history
from langchain_core.messages import HumanMessage
import logging


router = APIRouter()

print("starting")

@router.post('/generate_tutorial/')
async def generate_tutorial(request: ChatbotRequest, db: Session = Depends(get_db)):
    '''
    Handle POST requests to generate a tutorial based on user input,
    using Llama3 and storing the conversation in PostgreSQL.
    '''
    print("in endpoint")

    try:
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Use provided session_id or generate a new one if not provided
        session_id = request.session_id or str(uuid.uuid4())
        config = {"configurable": {"session_id": session_id}}
        prompt = request.prompt

        # Begin transaction
        db.begin()
        try:
            # Store user message
            user_message = ChatHistory(
                user_id=user.id,
                session_id=session_id,
                message=prompt,
                timestamp=datetime.utcnow(),
                is_user=True
            )
            db.add(user_message)
            db.flush()  # Flush to catch immediate insertion issues

            # Process the request using Llama3
            response = await with_message_history.invoke(
                [HumanMessage(content=prompt)],
                config=config,
            )

            # Store AI response
            ai_message = ChatHistory(
                user_id=user.id,
                session_id=session_id,
                message=response.content,
                timestamp=datetime.utcnow(),
                is_user=False
            )
            db.add(ai_message)
            db.commit()  # Commit all changes if everything is fine
        except:
            db.rollback()  # Rollback if any error occurs
            raise

        return {"tutorial": response.content, "session_id": session_id}

    except exc.SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error has occurred: {str(e)}")
