import os
from dotenv import load_dotenv
from groq import Groq

# Load environ  ment variables from .env file
load_dotenv()

groq_key = os.getenv("GROQ_KEY")
if not groq_key:
    raise ValueError("API key not found")

# Initialize Groq client
client = Groq(
    api_key=groq_key,
)