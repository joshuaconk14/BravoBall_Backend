from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import User, ChatHistory
from db import get_db
from auth import get_current_user
from sqlalchemy import distinct
import uuid

router = APIRouter()

@router.get("/conversations/")
def get_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversations = db.query(ChatHistory.session_id,
                             ChatHistory.timestamp,
                             ChatHistory.message)\
        .filter(ChatHistory.user_id == current_user.id)\
        .order_by(ChatHistory.session_id, ChatHistory.timestamp.desc())\
        .distinct(ChatHistory.session_id)\
        .all()
    
    return {
        "conversations": [
            {
                "id": str(conv.session_id),
                "title": conv.message['data']['content'][:50],  # Use first 50 chars of first message as title
                "createdAt": conv.timestamp.isoformat()
            } for conv in conversations
        ]
    }

@router.get("/conversations/{session_id}")
def get_conversation(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    messages = db.query(ChatHistory).filter(ChatHistory.user_id == current_user.id, ChatHistory.session_id == session_id).order_by(ChatHistory.timestamp).all()
    return {
        "id": session_id,
        "messages": [
            {
                "role": "user" if msg.is_user else "assistant", 
                "content": msg.message['data']['content']
            } for msg in messages
        ]
    }

@router.post("/conversations/new")
def new_conversation(current_user: User = Depends(get_current_user)):
    return {"session_id": str(uuid.uuid4())}
