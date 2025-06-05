"""
config.py
This file contains all the configuration for the application, including the NVIDIA API key, 
the model, and the secret key for hashing passwords
"""

import os
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# **** USER AUTHENTICATION ****
class UserAuth:
    SECRET_KEY = os.getenv('SECRET_KEY')
    ALGORITHM = os.getenv('ALGORITHM')
    ACCESS_TOKEN_EXPIRE_MINUTES = float(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 30))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', 30))
    # password hashing context
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")