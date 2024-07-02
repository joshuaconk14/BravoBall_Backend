import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()

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

def generate_tutorial(prompt):
    conversation = [
        {"role": "user", "parts": [{"text": "You are a soccer coach."}]},
        {"role": "user", "parts": [{"text": f"{prompt}. Provide the instructions in a single, coherent paragraph."}]}
    ]
    
    try:
        response = model.generate_content(conversation)
        tutorial = ''.join(part.text for part in response.parts).strip()
        return tutorial
    except Exception as e:
        return f"An error occurred: {str(e)}"

if __name__ == "__main__":
    test_prompt = "Provide a soccer training session plan"
    tutorial = generate_tutorial(test_prompt)
    print("Soccer Training Session")
    print("-----------------------")
    print(tutorial)
