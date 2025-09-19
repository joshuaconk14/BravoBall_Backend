#!/usr/bin/env python3
"""
quick_rollback.py
Quick rollback script for V2 migration - simple and easy to use
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent.parent / '.env')

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from migration_config import config
from rollback_manager import RollbackManager

def main():
    """Quick rollback to most recent backup"""
    try:
        print("🔄 Quick Rollback - Restoring to most recent backup")
        print("=" * 50)
        
        # Validate configuration
        if not config.validate():
            print("❌ Configuration validation failed")
            sys.exit(1)
        
        # Create rollback manager
        manager = RollbackManager(
            config.get_database_url("v2"),
            config.get_database_url("staging")
        )
        
        # Show available rollback points
        print("📋 Available rollback points:")
        rollback_points = manager.list_rollback_points()
        
        if not rollback_points:
            print("\n❌ No rollback points found!")
            print("💡 You can create a rollback point with:")
            print("   python3 rollback_manager.py <V2_URL> <STAGING_URL> create --description 'Before migration'")
            sys.exit(1)
        
        # Rollback to latest
        print(f"\n🎯 Rolling back to most recent point...")
        success = manager.rollback_latest(confirm=True)
        
        if success:
            print("\n✅ Rollback completed successfully!")
            print("🎯 Staging database has been restored to V2 state")
            print("💡 This provides a clean, consistent state for migration testing")
        else:
            print("\n❌ Rollback failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Rollback cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
