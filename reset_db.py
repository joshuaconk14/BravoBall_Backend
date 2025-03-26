"""
Reset database: Drop all tables, recreate them, and seed with initial data
"""
from sqlalchemy import create_engine, text
from models import Base
from db import SQLALCHEMY_DATABASE_URL

def reset_database():
    # Create engine
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    try:
        # Drop all tables with CASCADE
        with engine.connect() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
            connection.commit()
        print("✅ Successfully dropped all tables")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Successfully created all tables")
        
    except Exception as e:
        print(f"❌ Error resetting database: {str(e)}")
        raise e

if __name__ == "__main__":
    print("🔄 Resetting database...")
    reset_database()
    print("✨ Database reset complete!")