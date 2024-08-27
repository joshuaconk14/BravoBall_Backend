"""
memory_store.py
In-memory store initialized, prompt is pipelined into our model, and Runnable with 
session history is initialized
"""

from sqlalchemy.orm import Session
from models import ChatHistory
from db import get_db
from config import model
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from datetime import datetime


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful soccer assistant that gives concise responses.",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

max_messages = 10

class DatabaseChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id: str, db: Session):
        self.session_id = session_id
        self.db = db

    def add_message(self, message):
        chat_history = ChatHistory(
            session_id=self.session_id,
            message=message.content,
            timestamp=datetime.utcnow()
        )
        self.db.add(chat_history)
        self.db.commit()

    def clear(self):
        self.db.query(ChatHistory).filter(ChatHistory.session_id == self.session_id).delete()
        self.db.commit()

    @property
    def messages(self):
        return self.db.query(ChatHistory).filter(ChatHistory.session_id == self.session_id).order_by(ChatHistory.timestamp).all()

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    db = next(get_db())
    history = DatabaseChatMessageHistory(session_id, db)
    messages = history.messages
    if len(messages) > max_messages:
        for message in messages[:-max_messages]:
            db.delete(message)
        db.commit()
    return history

chain = prompt | model

with_message_history = RunnableWithMessageHistory(chain, get_session_history)