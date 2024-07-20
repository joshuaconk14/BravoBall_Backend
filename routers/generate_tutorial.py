from fastapi import APIRouter, HTTPException
from chatbot_config import model
from models import ChatbotRequest

router = APIRouter()

@router.post('/generate_tutorial/')
async def generate_tutorial(request: ChatbotRequest):

    # Try getting generated response from configured gemini model
    try:
        tutorial = model.generate_content("You are a soccer coach." f"Answer this question for them as if you are a polite soccer coach {request.prompt} for a player with details: {request.player_details}, act like a normal human thats friendly and conversative. If they ask for soccer training or technique advice, give the instructions in a single, coherent paragraph. only provide the instructions if necessary")
        return {"tutorial": tutorial.text}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error has occurred: {str(e)}")