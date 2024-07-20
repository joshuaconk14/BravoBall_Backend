from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging

import os
from dotenv import load_dotenv
import google.generativeai as genai


class PlayerDetails(BaseModel):
    name: str
    age: int
    position: str

class RequestModel(BaseModel):
    prompt: str
    player_details: PlayerDetails

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Retrieve the API key from the environment variable
api_key = os.getenv("GEMINI_KEY")
if not api_key:
    raise ValueError("API key not found")

# Configure the Gemini API key
genai.configure(api_key=api_key)

# Set up the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 0,
    "max_output_tokens": 500,
    "response_mime_type": "application/json"
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
]

model = genai.GenerativeModel(model_name='gemini-1.5-flash',
                              generation_config=generation_config,
                              safety_settings=safety_settings)

# Decorator function for POST FastAPI endpoint
@app.post("/generate_tutorial/")
# async def generate_tutorial(prompt: str, player_details: PlayerDetails):
async def generate_tutorial(request: RequestModel):

    conversation = [
        {"role": "user", "parts": [{"text": "You are a soccer coach."}]},
        {"role": "user", "parts": [{"text": f"{request.prompt} for a player with details: {request.player_details}. Provide the instructions in a single, coherent paragraph."}]}
    ]

    # try:
    #     if "Hello" in request.prompt:
    #         bot_response = "Hey!"
    #     elif "How are you" in request.prompt:
    #         bot_response = "Im doing well"  
    #     else:
    #         bot_response = "Oh oh ohhhhiiiiooooo!"

    #     return {
    #         "tutorial": bot_response
    #     }

    logger = logging.getLogger("my_debug_logger")
    # logger.debug(f"Conversation sent to model: {conversation}")

    try:
        # response = model.generate_content(conversation)
        tutorial = model.generate_content("You are a soccer coach." f"Answer this question for them as if you are a polite soccer coach {request.prompt} for a player with details: {request.player_details}, act like a normal human thats friendly and conversative. If they ask for soccer training or technique advice, give the instructions in a single, coherent paragraph. only provide the instructions if necessary")


        # logger.debug(f"Raw response from model: {tutorial}")

        # # parts = response.get('parts', [])
        # # tutorial = ' '.join(part.get('text', '') for part in parts).strip()
        # logger.warning(f"Generated tutorial: {tutorial}")

        return {"tutorial": tutorial.text}
    
    except Exception as e:
        # logger.error(f"Error generating tutorial: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error has occured: {str(e)}")

    # conversation = [
    #     {"role": "user", "parts": [{"text": "You are a soccer coach."}]},
    #     {"role": "user", "parts": [{"text": f"{prompt} for a player with details: {player_details}. Provide the instructions in a single, coherent paragraph."}]}
    # ]
    
    # try:
    #     response = model.generate_content(conversation)
    #     parts = response.get('parts', [])          
    #     tutorial = ' '.join(part.get('text', '') for part in parts).strip()              
    #     return {"tutorial": tutorial}             
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



# if __name__ == "__main__":
#     test_prompt = "Provide a soccer training session plan"
#     test_player_details = {
#         "name": "Joe Lolley",
#         "age": 18,
#         "position": "LW"
#     }
#     tutorial = generate_tutorial(test_prompt, test_player_details)
#     print("Soccer Training Session")
#     print("-----------------------")
#     print(tutorial)
