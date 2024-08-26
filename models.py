"""
models.py
This defines all models used in chatbot app
"""

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from db import Base

# Player details the user states in the frontend
class PlayerDetails(BaseModel):
    name: str
    age: int
    position: str

# Request model to be used in payload
class ChatbotRequest(BaseModel):
    user_id: int
    prompt: str 
    session_id: str = None
    
# Request model for profile creation
class PlayerInfo(BaseModel):
    first_name: str
    last_name: str
    age: int
    position: str
    email: str

# 
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    age = Column(Integer)
    position = Column(String)
    hashed_password = Column(String)
    player_details = Column(JSON)

    chat_histories = relationship("ChatHistory", back_populates="user")

class ChatHistory(Base):
    __tablename__ = "chat_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String, index=True)
    message = Column(String)
    timestamp = Column(DateTime)

    user = relationship("User", back_populates="chat_histories")