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

# Get the absolute path to your .env file
env_path = Path('.') / '.env'
# Load environment variables from .env file, override existing
load_dotenv(dotenv_path=env_path, override=True)

password = quote(os.getenv("POSTGRES_PASSWORD"))
username = os.getenv("POSTGRES_USER")
host = os.getenv("POSTGRES_HOST")
db = os.getenv("POSTGRES_DB")

# defining the database URL
SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{password}@{host}/{db}"

# creating the engine variable to connect to database
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# creating the session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

# this function is used to get the db session running
def get_db():
    db = SessionLocal()
    try:
        print(f"Connecting to database: {db}")
        yield db
    finally:
        db.close()