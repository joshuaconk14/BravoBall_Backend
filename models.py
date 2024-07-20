from pydantic import BaseModel

class PlayerDetails(BaseModel):
    name: str
    age: int
    position: str

class ChatbotRequest(BaseModel):
    prompt: str
    player_details: PlayerDetails