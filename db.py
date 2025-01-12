"""
db.py
This file defintes the database URL and starts the engine to initialize the db
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from urllib.parse import quote

import os
from dotenv import load_dotenv

load_dotenv()

password = quote(os.getenv("POSTGRES_PASSWORD"))
username = os.getenv("POSTGRES_USER")
host = os.getenv("POSTGRES_HOST")
db = os.getenv("POSTGRES_DB")


SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{password}@{host}/{db}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()