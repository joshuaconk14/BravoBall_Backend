"""
Reset database: Drop all tables, recreate them, and seed with initial data
"""
from sqlalchemy import create_engine, text
from models import Base
from db import SQLALCHEMY_DATABASE_URL
from config import get_logger

logger = get_logger(__name__)

def reset_database():
    # Create engine
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    try:
        # Drop all tables with CASCADE
        with engine.connect() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
            connection.commit()
        logger.info("✅ Successfully dropped all tables")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Successfully created all tables")
        
    except Exception as e:
        logger.error(f"❌ Error resetting database: {str(e)}")
        raise e

if __name__ == "__main__":
    logger.info("🔄 Resetting database...")
    reset_database()
    logger.info("✨ Database reset complete!")