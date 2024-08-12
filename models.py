from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings
from typing import List

class PlayerDetails(BaseModel):
    name: str
    age: int
    position: str

class BufferMessage(BaseModel):
    role: str
    content: str

class ChatbotRequest(BaseModel):
    prompt: str
    player_details: PlayerDetails
    