from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings
from typing import List

# Player details the user states in the frontend
class PlayerDetails(BaseModel):
    name: str
    age: int
    position: str

# Request model to be used in payload
class ChatbotRequest(BaseModel):
    prompt: str
    player_details: PlayerDetails
    