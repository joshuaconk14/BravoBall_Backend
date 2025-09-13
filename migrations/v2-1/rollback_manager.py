"""
rollback_manager.py
Provides safe rollback capabilities in case of migration issues
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add parent directory to path to import our models
sys.path.append(str(Path(__file__).parent.parent.parent))
from migration_config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(config.get_log_path("rollback_manager")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RollbackManager:
    """Handles rollback operations for migration safety"""
    
    def __init__(self, v2_url: str, staging_url: str):
        self.v2_engine = create_engine(v2_url)
        self.staging_engine = create_engine(staging_url)
        self.v2_session = self.v2_engine.connect()
        self.staging_session = self.staging_engine.connect()
        
        self.backup_dir = config.backup_dir
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_rollback_point(self) -> Optional[Path]:
        """Create a rollback point before migration"""
        try:
            logger.info("Creating rollback point...")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rollback_info = {
                'timestamp': timestamp,
                'created_at': datetime.now().isoformat(),
                'v2_database_url': str(self.v2_engine.url),
                'staging_database_url': str(self.staging_engine.url),
                'backups': {}
            }
            
            # Create full V2 database backup
            v2_backup_path = self.backup_dir / f"v2_full_backup_{timestamp}.dump"
            if self._create_database_backup(self.v2_engine.url, v2_backup_path):
                rollback_info['backups']['v2_full_backup'] = str(v2_backup_path)
                logger.info(f"V2 full backup created: {v2_backup_path}")
            else:
                logger.error("Failed to create V2 full backup")
                return None
            
            # Create staging database backup
            staging_backup_path = self.backup_dir / f"staging_backup_{timestamp}.dump"
            if self._create_database_backup(self.staging_engine.url, staging_backup_path):
                rollback_info['backups']['staging_backup'] = str(staging_backup_path)
                logger.info(f"Staging backup created: {staging_backup_path}")
            else:
                logger.error("Failed to create staging backup")
                return None
            
            # Create Android user data backup
            android_backup_path = self.backup_dir / f"android_users_backup_{timestamp}.json"
            if self._backup_android_users(android_backup_path):
                rollback_info['backups']['android_users_backup'] = str(android_backup_path)
                logger.info(f"Android users backup created: {android_backup_path}")
            else:
                logger.warning("Failed to create Android users backup")
            
            # Save rollback information
            rollback_info_path = self.backup_dir / f"rollback_info_{timestamp}.json"
            with open(rollback_info_path, 'w') as f:
                json.dump(rollback_info, f, indent=2)
            
            logger.info(f"✅ Rollback point created: {rollback_info_path}")
            return rollback_info_path
            
        except Exception as e:
            logger.error(f"Error creating rollback point: {e}")
            return None
    
    def _create_database_backup(self, database_url: str, backup_path: Path) -> bool:
        """Create a database backup using pg_dump"""
        try:
            cmd = [
                'pg_dump',
                database_url,
                '--format=custom',
                '--file', str(backup_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Database backup failed: {result.stderr}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            return False
    
    def _backup_android_users(self, backup_path: Path) -> bool:
        """Backup Android user data"""
        try:
            # Get Android users (users in V2 but not in V1)
            # For rollback purposes, we'll backup all V2 users
            with self.v2_session as conn:
                users = conn.execute(text("""
                    SELECT id, email, first_name, last_name, hashed_password,
                           primary_goal, biggest_challenge, training_experience,
                           position, playstyle, age_range, strengths,
                           areas_to_improve, training_location, available_equipment,
                           daily_training_time, weekly_training_days
                    FROM users
                """)).fetchall()
                
                user_data = []
                for user in users:
                    user_data.append({
                        'id': user[0],
                        'email': user[1],
                        'first_name': user[2],
                        'last_name': user[3],
                        'hashed_password': user[4],
                        'primary_goal': user[5],
                        'biggest_challenge': user[6],
                        'training_experience': user[7],
                        'position': user[8],
                        'playstyle': user[9],
                        'age_range': user[10],
                        'strengths': user[11],
                        'areas_to_improve': user[12],
                        'training_location': user[13],
                        'available_equipment': user[14],
                        'daily_training_time': user[15],
                        'weekly_training_days': user[16]
                    })
                
                with open(backup_path, 'w') as f:
                    json.dump(user_data, f, indent=2, default=str)
                
                return True
                
        except Exception as e:
            logger.error(f"Error backing up Android users: {e}")
            return False
    
    def list_rollback_points(self) -> List[Dict]:
        """List available rollback points"""
        try:
            rollback_files = list(self.backup_dir.glob("rollback_info_*.json"))
            rollback_points = []
            
            for file_path in rollback_files:
                try:
                    with open(file_path, 'r') as f:
                        rollback_info = json.load(f)
                    
                    rollback_points.append({
                        'file': str(file_path),
                        'timestamp': rollback_info.get('timestamp'),
                        'created_at': rollback_info.get('created_at'),
                        'backups': list(rollback_info.get('backups', {}).keys())
                    })
                except Exception as e:
                    logger.warning(f"Error reading rollback file {file_path}: {e}")
            
            # Sort by timestamp (newest first)
            rollback_points.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return rollback_points
            
        except Exception as e:
            logger.error(f"Error listing rollback points: {e}")
            return []
    
    def rollback_migration(self, rollback_info_file: Path) -> bool:
        """Rollback migration using a rollback point"""
        try:
            logger.info(f"Starting rollback using: {rollback_info_file}")
            
            # Load rollback information
            with open(rollback_info_file, 'r') as f:
                rollback_info = json.load(f)
            
            backups = rollback_info.get('backups', {})
            
            # Restore V2 database
            v2_backup = backups.get('v2_full_backup')
            if v2_backup and Path(v2_backup).exists():
                logger.info("Restoring V2 database...")
                if self._restore_database_backup(v2_backup, str(self.v2_engine.url)):
                    logger.info("✅ V2 database restored")
                else:
                    logger.error("❌ Failed to restore V2 database")
                    return False
            else:
                logger.error(f"V2 backup not found: {v2_backup}")
                return False
            
            # Restore staging database
            staging_backup = backups.get('staging_backup')
            if staging_backup and Path(staging_backup).exists():
                logger.info("Restoring staging database...")
                if self._restore_database_backup(staging_backup, str(self.staging_engine.url)):
                    logger.info("✅ Staging database restored")
                else:
                    logger.error("❌ Failed to restore staging database")
                    return False
            else:
                logger.warning(f"Staging backup not found: {staging_backup}")
            
            # Validate rollback
            if self._validate_rollback():
                logger.info("✅ Rollback completed successfully")
                return True
            else:
                logger.error("❌ Rollback validation failed")
                return False
            
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            return False
    
    def _restore_database_backup(self, backup_path: str, database_url: str) -> bool:
        """Restore database from backup"""
        try:
            # Drop and recreate database (be careful in production!)
            # For safety, we'll use pg_restore with --clean and --if-exists
            cmd = [
                'pg_restore',
                '--clean',
                '--if-exists',
                '--dbname', database_url,
                backup_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Database restore failed: {result.stderr}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error restoring database: {e}")
            return False
    
    def _validate_rollback(self) -> bool:
        """Validate that rollback was successful"""
        try:
            # Check that databases are accessible
            with self.v2_session as conn:
                v2_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
                logger.info(f"V2 users after rollback: {v2_count}")
            
            with self.staging_session as conn:
                staging_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
                logger.info(f"Staging users after rollback: {staging_count}")
            
            # Basic validation - databases should be accessible
            return v2_count is not None and staging_count is not None
            
        except Exception as e:
            logger.error(f"Error validating rollback: {e}")
            return False
    
    def cleanup_old_backups(self, days_to_keep: int = 7) -> int:
        """Clean up old backup files"""
        try:
            logger.info(f"Cleaning up backups older than {days_to_keep} days...")
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            deleted_count = 0
            
            # Clean up backup files
            for backup_file in self.backup_dir.glob("*"):
                if backup_file.is_file():
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        backup_file.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old backup: {backup_file}")
            
            logger.info(f"✅ Cleaned up {deleted_count} old backup files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")
            return 0
    
    def get_backup_info(self) -> Dict:
        """Get information about current backups"""
        try:
            backup_files = list(self.backup_dir.glob("*"))
            backup_info = {
                'total_files': len(backup_files),
                'total_size_mb': sum(f.stat().st_size for f in backup_files) / (1024 * 1024),
                'files': []
            }
            
            for file_path in backup_files:
                if file_path.is_file():
                    backup_info['files'].append({
                        'name': file_path.name,
                        'size_mb': file_path.stat().st_size / (1024 * 1024),
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
            
            return backup_info
            
        except Exception as e:
            logger.error(f"Error getting backup info: {e}")
            return {'error': str(e)}

def main():
    """Main function for command line usage"""
    if len(sys.argv) < 3:
        print("Usage: python rollback_manager.py <v2_database_url> <staging_database_url> <command> [options]")
        print("Commands:")
        print("  create                    - Create a new rollback point")
        print("  list                      - List available rollback points")
        print("  rollback <rollback_file>  - Rollback using specified file")
        print("  cleanup [days]            - Clean up old backups (default: 7 days)")
        print("  info                      - Show backup information")
        sys.exit(1)
    
    v2_url = sys.argv[1]
    staging_url = sys.argv[2]
    command = sys.argv[3]
    
    manager = RollbackManager(v2_url, staging_url)
    
    if command == "create":
        rollback_file = manager.create_rollback_point()
        if rollback_file:
            logger.info(f"Rollback point created: {rollback_file}")
            sys.exit(0)
        else:
            logger.error("Failed to create rollback point")
            sys.exit(1)
    
    elif command == "list":
        rollback_points = manager.list_rollback_points()
        if rollback_points:
            print("\nAvailable rollback points:")
            for point in rollback_points:
                print(f"  {point['file']} - {point['created_at']}")
        else:
            print("No rollback points found")
        sys.exit(0)
    
    elif command == "rollback":
        if len(sys.argv) < 5:
            print("Error: rollback command requires rollback file path")
            sys.exit(1)
        
        rollback_file = Path(sys.argv[4])
        if not rollback_file.exists():
            print(f"Error: rollback file not found: {rollback_file}")
            sys.exit(1)
        
        if manager.rollback_migration(rollback_file):
            logger.info("Rollback completed successfully")
            sys.exit(0)
        else:
            logger.error("Rollback failed")
            sys.exit(1)
    
    elif command == "cleanup":
        days = int(sys.argv[4]) if len(sys.argv) > 4 else 7
        deleted_count = manager.cleanup_old_backups(days)
        print(f"Cleaned up {deleted_count} old backup files")
        sys.exit(0)
    
    elif command == "info":
        info = manager.get_backup_info()
        print(json.dumps(info, indent=2))
        sys.exit(0)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
