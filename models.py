from pydantic import BaseModel
from typing import List

class Settings(BaseModel):
    api_key: str

    class Config:
        env_file = ".env"

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
    buffer: List[BufferMessage]
