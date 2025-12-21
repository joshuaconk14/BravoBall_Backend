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

# Load environment variables from .env file first
load_dotenv()

# Centralized logging configuration for production
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)

# Debug logging flag - controls whether detailed info logs are shown
# Set LOGGER_DEBUG=true for testing, false for production
LOGGER_DEBUG = os.getenv("LOGGER_DEBUG", "false").lower() == "true"

def get_logger(name=None):
    """Get a logger with the specified name, using the centralized config."""
    return logging.getLogger(name)

def log_debug(logger, message, *args, **kwargs):
    """
    Conditionally log info messages based on LOGGER_DEBUG flag.
    Use this for detailed debug logs that should only appear when debugging is enabled.
    When LOGGER_DEBUG=false, these logs are suppressed.
    When LOGGER_DEBUG=true, these logs are shown.
    """
    if LOGGER_DEBUG:
        logger.info(message, *args, **kwargs)

def log_debug_error(logger, message, *args, **kwargs):
    """
    Conditionally log error messages based on LOGGER_DEBUG flag.
    Use this for receipt verification error logs that should only appear when debugging is enabled.
    When LOGGER_DEBUG=false, these logs are suppressed.
    When LOGGER_DEBUG=true, these logs are shown.
    """
    if LOGGER_DEBUG:
        logger.error(message, *args, **kwargs)

def log_debug_warning(logger, message, *args, **kwargs):
    """
    Conditionally log warning messages based on LOGGER_DEBUG flag.
    Use this for receipt verification warning logs that should only appear when debugging is enabled.
    When LOGGER_DEBUG=false, these logs are suppressed.
    When LOGGER_DEBUG=true, these logs are shown.
    """
    if LOGGER_DEBUG:
        logger.warning(message, *args, **kwargs)

# **** USER AUTHENTICATION ****
class UserAuth:
    SECRET_KEY = os.getenv('SECRET_KEY')
    ALGORITHM = os.getenv('ALGORITHM')
    ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes
    REFRESH_TOKEN_EXPIRE_DAYS = 90  # 90 days
    # password hashing context
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# **** REVENUECAT CONFIGURATION ****
class RevenueCat:
    API_KEY = os.getenv("REVENUECAT_API_KEY")
    API_URL = "https://api.revenuecat.com/v1"
    # Allow simulator purchases to bypass RevenueCat verification (development/testing only)
    # Set to True to allow StoreKit simulator transactions without RevenueCat verification
    ALLOW_SIMULATOR_BYPASS = os.getenv("REVENUECAT_ALLOW_SIMULATOR_BYPASS", "false").lower() == "true"
    
    # Product ID to treat amount mapping for validation
    # This ensures clients can't manipulate treat amounts
    PRODUCT_TREAT_MAPPING = {
        "bravoball_treats_500": 500,
        "bravoball_treats_1000": 1000,
        "bravoball_treats_2000": 2000,
        # Add more product IDs as needed
    }