"""
create_tables.py
This file is ran once to create tables for postgres db

Logging level can be set via the LOG_LEVEL environment variable (e.g., LOG_LEVEL=WARNING) for production best practices.
"""

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
import models
from db import SQLALCHEMY_DATABASE_URL
from config import get_logger

logger = get_logger(__name__)

def create_tables():
    # Create an engine
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    inspector = inspect(engine)
    
    # Get list of existing tables
    existing_tables = inspector.get_table_names()
    
    # List of new tables we want to create
    new_tables = ["drill_categories", "drills"]
    
    # Print status for each table
    for table in new_tables:
        if table in existing_tables:
            logger.info(f"Table '{table}' already exists")
        else:
            logger.info(f"Creating table '{table}'...")
    
    try:    
        # This will only create tables that don't exist
        models.Base.metadata.create_all(bind=engine)
        logger.info("\nTable creation completed successfully!")
    except Exception as e:
        logger.error(f"\nError creating tables: {str(e)}")

if __name__ == "__main__":
    create_tables()