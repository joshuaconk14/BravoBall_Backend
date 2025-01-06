"""
create_tables.py
This file is ran once to create tables for postgres db
"""

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
import models
from db import SQLALCHEMY_DATABASE_URL

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
            print(f"Table '{table}' already exists")
        else:
            print(f"Creating table '{table}'...")
    
    try:    
        # This will only create tables that don't exist
        models.Base.metadata.create_all(bind=engine)
        print("\nTable creation completed successfully!")
    except Exception as e:
        print(f"\nError creating tables: {str(e)}")

if __name__ == "__main__":
    create_tables()