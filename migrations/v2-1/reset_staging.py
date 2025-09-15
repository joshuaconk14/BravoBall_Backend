#!/usr/bin/env python3
"""
reset_staging.py
Simple script to clear and repopulate staging database from V2
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from migration_config import config
from staging_setup import StagingSetup

def reset_staging():
    """Clear staging database and repopulate it from V2"""
    try:
        print("🔄 Resetting staging database...")
        
        # Validate configuration
        if not config.validate():
            print("❌ Configuration validation failed")
            return False
        
        # Create staging setup instance
        setup = StagingSetup(config.get_database_url("v2"), config.get_database_url("staging"))
        
        # Clear and repopulate staging
        print("🗑️  Clearing staging database...")
        if not setup.clear_staging_database():
            print("❌ Failed to clear staging database")
            return False
        
        print("📋 Copying V2 data to staging...")
        if not setup.copy_data_from_source():
            print("❌ Failed to copy data from source")
            return False
        
        print("✅ Staging database reset completed successfully!")
        print(f"   Staging now contains fresh copy of V2 data")
        return True
        
    except Exception as e:
        print(f"❌ Error resetting staging: {e}")
        return False

if __name__ == "__main__":
    if reset_staging():
        print("\n🎯 Ready to run test migration!")
        sys.exit(0)
    else:
        print("\n💥 Staging reset failed!")
        sys.exit(1)
