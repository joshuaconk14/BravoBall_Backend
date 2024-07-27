from fastapi import APIRouter, HTTPException
# from chatbot_config import model
from groq_llama3 import client
from models import ChatbotRequest
from langchain.memory.buffer import ConversationBufferMemory

router = APIRouter()

@router.post('/generate_tutorial/')
async def generate_tutorial(request: ChatbotRequest):

    # Try getting generated response from configured gemini model
    try:
        # Extract player details
        name = request.player_details.name
        age = request.player_details.age
        position = request.player_details.position

        # Generate chat completion using Groq
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": f"Player details: name is {name}, age is {str(age)}, position is {position}. {request.prompt}",
                }
            ],
            model="llama3-8b-8192",
        )
        tutorial = chat_completion.choices[0].message.content

        return {"tutorial": tutorial}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error has occurred: {str(e)}")
