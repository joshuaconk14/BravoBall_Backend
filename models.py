from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    groq_api_key: str = Field(..., env="GROQ_KEY")

    class Config:
        env_file = ".env"

# try:
#     settings = Settings()
#     print(f"GROQ_KEY: {settings.groq_api_key}")
# except ValidationError as e:
#     print("Validation Error:", e.errors())

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
    