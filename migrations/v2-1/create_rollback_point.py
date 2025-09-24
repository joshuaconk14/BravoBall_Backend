#!/usr/bin/env python3
"""
create_rollback_point.py
Create a rollback point before running migrations
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
    """Create a rollback point"""
    try:
        print("🔄 Creating Rollback Point")
        print("=" * 30)
        
        # Validate configuration
        if not config.validate():
            print("❌ Configuration validation failed")
            sys.exit(1)
        
        # Determine target database based on environment or command line args
        # Check if we're in production mode
        is_production = os.getenv("MIGRATION_DEBUG", "true").lower() == "false" or "--production" in sys.argv
        
        if is_production:
            # Production mode: create rollback point for V2 database
            target_db = "v2"
            source_db = "staging"  # Not used for backup creation, but required by RollbackManager
            print("🏭 PRODUCTION MODE: Creating rollback point for V2 production database")
        else:
            # Development mode: create rollback point for staging database  
            target_db = "staging"
            source_db = "v2"
            print("🧪 DEVELOPMENT MODE: Creating rollback point for staging database")
        
        # Get description from user
        description = input("Enter description for this rollback point (or press Enter for default): ").strip()
        if not description:
            description = f"Rollback point created at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Create rollback manager
        manager = RollbackManager(
            config.get_database_url(target_db),
            config.get_database_url(source_db)
        )
        
        # Create rollback point
        backup_path = manager.create_rollback_point(description)
        
        if backup_path:
            print(f"\n✅ Rollback point created successfully!")
            print(f"📦 Backup file: {backup_path.name}")
            print(f"📝 Description: {description}")
            print(f"\n💡 To rollback later, run:")
            print(f"   python3 quick_rollback.py")
        else:
            print("\n❌ Failed to create rollback point!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    from datetime import datetime
    main()
