"""
generate_tutorial.py
Endpoint listening for POST requests from frontend, handles user questions and uses Runnable from
memory_store.py to communicate with Llama3, while integrating with a PostgreSQL database
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
import uuid
from models import ChatbotRequest, User, ChatHistory
from db import get_db
from memory_store import with_message_history
from langchain_core.messages import HumanMessage

router = APIRouter()

@router.post('/generate_tutorial/')
def generate_tutorial(request: ChatbotRequest, db: Session = Depends(get_db)):
    try:
        # print(f"user id: {request.user_id}")
        stmt = select(User).where(User.id == request.user_id)
        user = db.execute(stmt).scalars().first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        print("HERE1")
        session_id = request.session_id or str(uuid.uuid4())
        config = {"configurable": {"session_id": session_id}}
        prompt = request.prompt

        user_message = ChatHistory(
            user_id=user.id,
            session_id=session_id,
            message={"type": "human", "data": {"content": prompt}},
            timestamp=datetime.utcnow(),
            is_user=True
        )
        db.add(user_message)
        db.flush()
        print("HERE2")

        try:
            print("Invoking model with session_id:", session_id)
            print("Config:", config)
            response = with_message_history.invoke(
                [HumanMessage(content=prompt)],
                config=config,
            )
        except Exception as e:
            print("Error during model invocation:", str(e))
            raise HTTPException(status_code=500, detail=str(e))

        print("HERE3")
        ai_message = ChatHistory(
            user_id=user.id,
            session_id=session_id,
            message={"type": "ai", "data": {"content": response.content}},
            timestamp=datetime.utcnow(),
            is_user=False
        )
        # Delete rows where is_user is null
        db.query(ChatHistory).filter(ChatHistory.is_user.is_(None)).delete()
        db.add(ai_message)
        db.commit()

        return {"tutorial": response.content, "session_id": session_id}

    except Exception as e:
        db.rollback()
        print(f"Error in generate_tutorial: {e}")
        raise HTTPException(status_code=500, detail=str(e))
