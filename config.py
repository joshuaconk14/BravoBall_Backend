"""
config.py
This file contains all the configuration for the application, including the NVIDIA API key, 
the model, and the secret key for hashing passwords
"""

import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# **** USER AUTHENTICATION ****
class UserAuth:
    SECRET_KEY = os.getenv('SECRET_KEY')
    ALGORITHM = os.getenv('ALGORITHM')
    ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES')
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")