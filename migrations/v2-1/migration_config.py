"""
migration_config.py
Configuration management for V2 migration
"""

import os
from typing import Optional
from pathlib import Path
import json
from datetime import datetime

class MigrationConfig:
    """Configuration for V2 migration process"""
    
    def __init__(self):
        self.v1_database_url = os.getenv("V1_DATABASE_URL")
        self.v2_database_url = os.getenv("V2_DATABASE_URL") 
        self.staging_database_url = os.getenv("STAGING_DATABASE_URL")
        
        # Debug/testing mode - set to False for production
        self.debug_mode = os.getenv("MIGRATION_DEBUG", "true").lower() == "true"
        
        # Test with limited users in debug mode
        self.max_test_users = int(os.getenv("MAX_TEST_USERS", "5"))
        
        # Android user backup limit in debug mode (for testing simplicity)
        self.max_android_backup_users = int(os.getenv("MAX_ANDROID_BACKUP_USERS", "5"))
        
        # Migration settings
        self.android_cutoff_date = "2024-09-01"  # Android users created after this date
        self.stale_data_date = "2024-07-28"      # When stale data was copied to V2
        
        # Backup settings
        self.backup_dir = Path(__file__).parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Logging
        self.log_dir = Path(__file__).parent / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
    def validate(self) -> bool:
        """Validate that all required configuration is present"""
        required_vars = [
            ("V1_DATABASE_URL", self.v1_database_url),
            ("V2_DATABASE_URL", self.v2_database_url),
            ("STAGING_DATABASE_URL", self.staging_database_url)
        ]
        
        missing = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing.append(var_name)
        
        if missing:
            print(f"❌ Missing required environment variables: {', '.join(missing)}")
            print("\nPlease set the following environment variables:")
            for var in missing:
                print(f"  export {var}=<your_database_url>")
            return False
            
        return True
    
    def get_database_url(self, environment: str) -> str:
        """Get database URL for specific environment"""
        urls = {
            "v1": self.v1_database_url,
            "v2": self.v2_database_url,
            "staging": self.staging_database_url
        }
        
        if environment not in urls:
            raise ValueError(f"Unknown environment: {environment}")
            
        url = urls[environment]
        if not url:
            raise ValueError(f"Database URL not configured for {environment}")
            
        return url
    
    def is_debug_mode(self) -> bool:
        """Check if running in debug/testing mode"""
        return self.debug_mode
    
    def get_test_user_limit(self) -> int:
        """Get maximum number of users to process in test mode"""
        return self.max_test_users if self.is_debug_mode() else None
    
    def get_android_backup_limit(self) -> int:
        """Get maximum number of Android users to backup in debug mode"""
        return self.max_android_backup_users if self.is_debug_mode() else None
    
    def get_backup_path(self, backup_type: str) -> Path:
        """Get path for backup file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.backup_dir / f"{backup_type}_{timestamp}.json"
    
    def get_log_path(self, log_type: str) -> Path:
        """Get path for log file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.log_dir / f"{log_type}_{timestamp}.log"
    
    def save_config(self, filepath: Optional[Path] = None) -> Path:
        """Save current configuration to file"""
        if filepath is None:
            filepath = self.backup_dir / f"migration_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        config_data = {
            "v1_database_url": self.v1_database_url,
            "v2_database_url": self.v2_database_url,
            "staging_database_url": self.staging_database_url,
            "debug_mode": self.debug_mode,
            "max_test_users": self.max_test_users,
            "max_android_backup_users": self.max_android_backup_users,
            "android_cutoff_date": self.android_cutoff_date,
            "stale_data_date": self.stale_data_date,
            "created_at": datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(config_data, f, indent=2)
            
        return filepath
    
    def load_config(self, filepath: Path) -> dict:
        """Load configuration from file"""
        with open(filepath, 'r') as f:
            return json.load(f)

# Global config instance
config = MigrationConfig()
