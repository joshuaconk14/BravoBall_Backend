"""
config.py
This file contains all the configuration for the application, including the NVIDIA API key, 
the model, and the secret key for hashing passwords

To change log level, set the LOG_LEVEL environment variable (e.g., LOG_LEVEL=WARNING)
"""

import os
from passlib.context import CryptContext
from dotenv import load_dotenv
import logging

# Centralized logging configuration for production
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)

def get_logger(name=None):
    """Get a logger with the specified name, using the centralized config."""
    return logging.getLogger(name)

load_dotenv()

# **** USER AUTHENTICATION ****
class UserAuth:
    SECRET_KEY = os.getenv('SECRET_KEY')
    ALGORITHM = os.getenv('ALGORITHM')
    ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes
    REFRESH_TOKEN_EXPIRE_DAYS = 90  # 90 days
    # password hashing context
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")