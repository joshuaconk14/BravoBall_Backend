"""
db.py
This file defintes the database URL and starts the engine to initialize the db
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from urllib.parse import quote

password = quote("Br@v0l1nski192jnc")

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:{password}@localhost/postgres"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()