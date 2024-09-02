"""
config.py
This file contains all the configuration for the application, including the NVIDIA API key, 
the model, and the secret key for hashing passwords
"""


import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from passlib.context import CryptContext

# Obtain NVIDIA api key
NVAPI_KEY = os.getenv('NVAPI_KEY')
if not NVAPI_KEY:
    raise ValueError("API key not found")

# Initialize ChatNVIDIA client to connect with Llama3
model = ChatNVIDIA(
  model="meta/llama-3.1-8b-instruct",
  api_key=NVAPI_KEY, 
  temperature=0.2,
  top_p=0.7,
  max_tokens=1024,
)

# TODO: make better key, store safely
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")