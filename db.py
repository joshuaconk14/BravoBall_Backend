"""
db.py
This file defintes the database URL and starts the engine to initialize the db
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import quote

import os
from dotenv import load_dotenv
from pathlib import Path
from config import get_logger

# Get the database URL from the environment variables
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    # Fallback to local development variables
    env_path = Path('.') / '.env'
    load_dotenv(dotenv_path=env_path, override=True)
    from urllib.parse import quote
    password = quote(os.getenv("POSTGRES_PASSWORD", ""))
    username = os.getenv("POSTGRES_USER", "")
    host = os.getenv("POSTGRES_HOST", "")
    db = os.getenv("POSTGRES_DB", "")
    SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{password}@{host}/{db}"

# creating the engine variable to connect to database
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# creating the session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

logger = get_logger(__name__)

# this function is used to get the db session running
def get_db():
    db = SessionLocal()
    try:
        logger.info(f"Connecting to database: {db}")
        yield db
    finally:
        db.close()