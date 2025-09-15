#!/usr/bin/env python3
"""
test_specific_user.py
Test migration on a specific user (jordan@test.com)
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from migration_config import config
from v2_migration_manager import V2MigrationManager
from models import User
from models_v1 import UserV1
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

def test_specific_user(email=None):
    """Test migration on a specific user"""
    try:
        # Use command line argument if provided, otherwise use default
        if not email:
            email = sys.argv[1] if len(sys.argv) > 1 else "jordan@test.com"
        
        print(f"🧪 Testing migration on {email}...")
        
        # Validate configuration
        if not config.validate():
            print("❌ Configuration validation failed")
            return False
        
        # Create migration manager
        migration_manager = V2MigrationManager(
            config.get_database_url("v1"),
            config.get_database_url("staging")  # Use staging as V2 for testing
        )
        
        print(f"📧 Testing migration for: {email}")
        
        # Check if user exists in V1
        v1_user = migration_manager.v1_session.query(UserV1).filter(
            UserV1.email.ilike(email)
        ).first()
        
        if not v1_user:
            print(f"❌ User {email} not found in V1 database")
            return False
        
        print(f"✅ User found in V1: {v1_user.email}")
        
        # Check if user exists in staging
        staging_user = migration_manager.v2_session.query(User).filter(
            User.email.ilike(email)
        ).first()
        
        if staging_user:
            print(f"✅ User found in staging: {staging_user.email} (ID: {staging_user.id})")
            print("🔄 Running overwrite migration (delete + recreate)...")
            
            # Run the overwrite migration
            success = migration_manager._migrate_apple_user_overwrite(email)
            if success:
                print(f"✅ Successfully migrated {email}")
                return True
            else:
                print(f"❌ Failed to migrate {email}")
                return False
        else:
            print(f"ℹ️  User {email} not found in staging database - no stale data")
            print("🔄 Running create migration...")
            
            # Run the create migration
            success = migration_manager._migrate_apple_user_create(email)
            if success:
                print(f"✅ Successfully created {email}")
                return True
            else:
                print(f"❌ Failed to create {email}")
                return False
            
    except Exception as e:
        logger.error(f"Error testing specific user: {e}")
        return False
    finally:
        # Clean up sessions
        try:
            migration_manager.v1_session.close()
            migration_manager.v2_session.close()
        except:
            pass

if __name__ == "__main__":
    success = test_specific_user()
    if success:
        print("\n🎉 Test completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Test failed!")
        sys.exit(1)
