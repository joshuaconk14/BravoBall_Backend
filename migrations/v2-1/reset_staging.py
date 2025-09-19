#!/usr/bin/env python3
"""
reset_staging.py
Simple script to clear and repopulate staging database from V2
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from datetime import datetime

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent.parent / '.env')

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from migration_config import config
from staging_setup import StagingSetup

# Set up detailed logging
log_file = config.log_dir / f"reset_staging_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def reset_staging():
    """Clear staging database and repopulate it from V2"""
    try:
        logger.info("🔄 Starting staging database reset...")
        print("🔄 Resetting staging database...")
        
        # Validate configuration
        logger.info("Validating configuration...")
        if not config.validate():
            logger.error("Configuration validation failed")
            print("❌ Configuration validation failed")
            return False
        
        # Log database URLs (without passwords)
        v2_url = config.get_database_url("v2")
        staging_url = config.get_database_url("staging")
        logger.info(f"V2 URL: {v2_url.split('@')[0]}@***")
        logger.info(f"Staging URL: {staging_url.split('@')[0]}@***")
        
        # Create staging setup instance
        logger.info("Creating StagingSetup instance...")
        setup = StagingSetup(v2_url, staging_url)
        
        # Check current state before clearing
        logger.info("Checking current staging database state...")
        from sqlalchemy import create_engine, text
        staging_engine = create_engine(staging_url)
        with staging_engine.connect() as conn:
            user_count_before = conn.execute(text('SELECT COUNT(*) FROM users')).scalar()
            logger.info(f"Users in staging before reset: {user_count_before}")
        
        # Clear and repopulate staging
        logger.info("Clearing staging database...")
        print("🗑️  Clearing staging database...")
        if not setup.clear_staging_database():
            logger.error("Failed to clear staging database")
            print("❌ Failed to clear staging database")
            return False
        
        # Check state after clearing
        with staging_engine.connect() as conn:
            user_count_after_clear = conn.execute(text('SELECT COUNT(*) FROM users')).scalar()
            logger.info(f"Users in staging after clearing: {user_count_after_clear}")
        
        logger.info("Copying V2 data to staging...")
        print("📋 Copying V2 data to staging...")
        if not setup.copy_data_from_source():
            logger.error("Failed to copy data from source")
            print("❌ Failed to copy data from source")
            return False
        
        # Check final state
        with staging_engine.connect() as conn:
            user_count_final = conn.execute(text('SELECT COUNT(*) FROM users')).scalar()
            logger.info(f"Users in staging after copy: {user_count_final}")
        
        logger.info("Staging database reset completed successfully!")
        print("✅ Staging database reset completed successfully!")
        print(f"   Staging now contains fresh copy of V2 data")
        return True
        
    except Exception as e:
        logger.error(f"Error resetting staging: {e}", exc_info=True)
        print(f"❌ Error resetting staging: {e}")
        return False

if __name__ == "__main__":
    if reset_staging():
        print("\n🎯 Ready to run test migration!")
        sys.exit(0)
    else:
        print("\n💥 Staging reset failed!")
        sys.exit(1)
