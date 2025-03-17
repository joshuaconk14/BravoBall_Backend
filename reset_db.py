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
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        print("✅ Successfully dropped all tables")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Successfully created all tables")
        
        # # Seed drills
        # seed_drills()
        # print("✅ Successfully seeded database")
        
    except Exception as e:
        print(f"❌ Error resetting database: {str(e)}")
        raise e

if __name__ == "__main__":
    print("🔄 Resetting database...")
    reset_database()
    print("✨ Database reset complete!")