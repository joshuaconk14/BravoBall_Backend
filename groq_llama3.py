import os

from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env file
load_dotenv()

groq_key = os.getenv("GROQ_KEY")
if not groq_key:
    raise ValueError("API key not found")

# Initialize Groq client
client = Groq(
    api_key=groq_key,
)

name = "Joe"
age = 18

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": f"Give a tutorial for soccer players with player details: name is {name} and age is {str(age)}",
        }
    ],
    model="llama3-8b-8192",
)

print(chat_completion.choices[0].message.content)