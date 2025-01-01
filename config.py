"""
config.py
This file contains all the configuration for the application, including the NVIDIA API key, 
the model, and the secret key for hashing passwords
"""

import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env', verbose=True)

# **** USER AUTHENTICATION ****

# Get SECRET_KEY from environment variables
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY not found in environment variables")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# **** CHATBOT CONFIGURATION (use later) ****

# Obtain NVIDIA api key
NVAPI_KEY = os.getenv('NVAPI_KEY')
if not NVAPI_KEY:
    raise ValueError("NVAPI_KEY not found in environment variables")

# Initialize ChatNVIDIA client to connect with Llama3
model = ChatNVIDIA(
  model="meta/llama-3.1-8b-instruct",
  api_key=NVAPI_KEY, 
  temperature=0.2,
  top_p=0.7,
  max_tokens=1024,
)
