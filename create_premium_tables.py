"""
create_premium_tables.py
Script to create premium subscription tables in the database
"""

from sqlalchemy import create_engine, text
from db import SQLALCHEMY_DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_premium_tables():
    """Create premium subscription tables"""
    try:
        # Create engine
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        
        with engine.connect() as connection:
            # Create premium_subscriptions table
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS premium_subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    status VARCHAR(50) NOT NULL DEFAULT 'free',
                    plan_type VARCHAR(50) NOT NULL DEFAULT 'free',
                    start_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    end_date TIMESTAMP,
                    trial_end_date TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    platform VARCHAR(20),
                    receipt_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Create usage_tracking table
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS usage_tracking (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    feature_type VARCHAR(50) NOT NULL,
                    usage_count INTEGER DEFAULT 1,
                    usage_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Create indexes for better performance
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_premium_subscriptions_user_id 
                ON premium_subscriptions(user_id);
            """))
            
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_premium_subscriptions_status 
                ON premium_subscriptions(status);
            """))
            
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_usage_tracking_user_id 
                ON usage_tracking(user_id);
            """))
            
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_usage_tracking_feature_date 
                ON usage_tracking(user_id, feature_type, usage_date);
            """))
            
            # Commit the changes
            connection.commit()
            
            logger.info("Premium subscription tables created successfully!")
            
            # Verify tables exist
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('premium_subscriptions', 'usage_tracking')
                ORDER BY table_name;
            """))
            
            tables = [row[0] for row in result]
            logger.info(f"Created tables: {tables}")
            
    except Exception as e:
        logger.error(f"Error creating premium tables: {str(e)}")
        raise

def create_default_subscriptions():
    """Create default free subscriptions for existing users"""
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        
        with engine.connect() as connection:
            # Get all users who don't have a premium subscription
            result = connection.execute(text("""
                SELECT u.id 
                FROM users u 
                LEFT JOIN premium_subscriptions ps ON u.id = ps.user_id 
                WHERE ps.id IS NULL;
            """))
            
            user_ids = [row[0] for row in result]
            
            if user_ids:
                # Create default free subscriptions
                for user_id in user_ids:
                    connection.execute(text("""
                        INSERT INTO premium_subscriptions 
                        (user_id, status, plan_type, start_date, is_active) 
                        VALUES (:user_id, 'free', 'free', CURRENT_TIMESTAMP, TRUE);
                    """), {"user_id": user_id})
                
                connection.commit()
                logger.info(f"Created default free subscriptions for {len(user_ids)} users")
            else:
                logger.info("All users already have premium subscriptions")
                
    except Exception as e:
        logger.error(f"Error creating default subscriptions: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        logger.info("Starting premium table creation...")
        create_premium_tables()
        
        logger.info("Creating default subscriptions for existing users...")
        create_default_subscriptions()
        
        logger.info("Premium system setup completed successfully!")
        
    except Exception as e:
        logger.error(f"Premium system setup failed: {str(e)}")
        exit(1)
