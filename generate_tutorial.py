from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import os
from dotenv import load_dotenv
import google.generativeai as genai


class PlayerDetails(BaseModel):
    name: str
    age: int
    position: str


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

model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                              generation_config=generation_config,
                              safety_settings=safety_settings)

@app.post("/generate_tutorial/")
async def generate_tutorial(prompt: str, player_details: PlayerDetails):
    conversation = [
        {"role": "user", "parts": [{"text": "You are a soccer coach."}]},
        {"role": "user", "parts": [{"text": f"{prompt} for a player with details: {player_details}. Provide the instructions in a single, coherent paragraph."}]}
    ]
    
    try:
        response = model.generate_content(conversation)
        parts = response.get('parts', [])
        
        tutorial = ' '.join(part.get('text', '') for part in parts).strip()
        
        return {"tutorial": tutorial}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

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
