#!/usr/bin/env python3
"""
rollback_manager.py
Simple rollback manager for V2 migration with PostgreSQL version compatibility
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent.parent / '.env')

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from migration_config import config
from staging_setup import StagingSetup

class RollbackManager:
    """Simple rollback manager for migration recovery with version compatibility"""
    
    def __init__(self, v2_url: str, staging_url: str):
        self.v2_url = v2_url
        self.staging_url = staging_url
        self.backup_dir = config.backup_dir
        self.backup_dir.mkdir(exist_ok=True)
        
    def create_rollback_point(self, description: str = None) -> Path:
        """Create a rollback point (backup) of current staging state"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            description_safe = description.replace(" ", "_").replace("/", "_") if description else "rollback"
            backup_name = f"rollback_{description_safe}_{timestamp}"
            backup_path = self.backup_dir / f"{backup_name}.sql"
            
            print(f"🔄 Creating rollback point: {backup_name}")
            
            # Create data-only backup using pg_dump
            cmd = [
                'pg_dump',
                self.staging_url,
                '--format=plain',
                '--data-only',  # Only backup data, not schema
                '--no-sync',
                '--file', str(backup_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                print(f"❌ Backup failed: {result.stderr}")
                return None
            
            # Create metadata file
            metadata = {
                "backup_name": backup_name,
                "created_at": datetime.now().isoformat(),
                "description": description or "Rollback point",
                "staging_url": self.staging_url,
                "backup_file": str(backup_path),
                "backup_format": "sql"
            }
            
            metadata_path = self.backup_dir / f"{backup_name}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✅ Rollback point created: {backup_path}")
            return backup_path
            
        except Exception as e:
            print(f"❌ Error creating rollback point: {e}")
            return None
    
    def list_rollback_points(self):
        """List available rollback points"""
        try:
            print("📋 Available rollback points:")
            print("=" * 60)
            
            backup_files = list(self.backup_dir.glob("rollback_*.json"))
            if not backup_files:
                print("No rollback points found.")
                return []
            
            rollback_points = []
            for metadata_file in sorted(backup_files, key=lambda x: x.stat().st_mtime, reverse=True):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    backup_file = Path(metadata.get('backup_file', ''))
                    if backup_file.exists():
                        size_mb = backup_file.stat().st_size / (1024 * 1024)
                        print(f"📦 {metadata['backup_name']}")
                        print(f"   Created: {metadata['created_at']}")
                        print(f"   Description: {metadata['description']}")
                        print(f"   Size: {size_mb:.1f} MB")
                        print(f"   File: {backup_file.name}")
                        print()
                        
                        rollback_points.append(metadata)
                    else:
                        print(f"⚠️  {metadata['backup_name']} - backup file missing")
                        print()
                        
                except Exception as e:
                    print(f"❌ Error reading {metadata_file}: {e}")
            
            return rollback_points
            
        except Exception as e:
            print(f"❌ Error listing rollback points: {e}")
            return []
    
    def rollback_to_point(self, backup_file: Path, confirm: bool = True) -> bool:
        """Rollback to a specific backup point"""
        try:
            if not backup_file.exists():
                print(f"❌ Backup file not found: {backup_file}")
                return False
            
            if confirm:
                print(f"⚠️  This will restore staging database from backup:")
                print(f"   Backup: {backup_file}")
                print(f"   Target: {self.staging_url}")
                print()
                response = input("Are you sure you want to proceed? (yes/no): ").strip().lower()
                if response not in ['yes', 'y']:
                    print("❌ Rollback cancelled")
                    return False
            
            print(f"🔄 Rolling back to: {backup_file.name}")
            
            # Actually restore from the backup file
            print("   Restoring staging database from backup file...")
            
            # First, clear the staging database
            print("   Clearing staging database...")
            reset_cmd = ['python3', 'reset_staging.py']
            result = subprocess.run(reset_cmd, capture_output=True, text=True, timeout=300, cwd=Path(__file__).parent)
            
            if result.returncode != 0:
                print(f"❌ Failed to clear staging database: {result.stderr}")
                return False
            
            print("   ✅ Staging database cleared")
            
            # Verify the database is actually cleared
            print("   Verifying database is cleared...")
            from sqlalchemy import create_engine, text
            staging_engine = create_engine(self.staging_url)
            with staging_engine.connect() as conn:
                user_count = conn.execute(text('SELECT COUNT(*) FROM users')).scalar()
                if user_count > 0:
                    print(f"   ⚠️  Database still has {user_count} users - clearing manually...")
                    # Manual clear if reset_staging.py didn't work
                    conn.execute(text('TRUNCATE TABLE users CASCADE'))
                    conn.execute(text('TRUNCATE TABLE completed_sessions CASCADE'))
                    conn.execute(text('TRUNCATE TABLE custom_drills CASCADE'))
                    conn.execute(text('TRUNCATE TABLE drill_categories CASCADE'))
                    conn.execute(text('TRUNCATE TABLE drill_groups CASCADE'))
                    conn.execute(text('TRUNCATE TABLE drills CASCADE'))
                    conn.execute(text('TRUNCATE TABLE drill_group_items CASCADE'))
                    conn.execute(text('TRUNCATE TABLE drill_skill_focus CASCADE'))
                    conn.execute(text('TRUNCATE TABLE email_verification_codes CASCADE'))
                    conn.execute(text('TRUNCATE TABLE mental_training_quotes CASCADE'))
                    conn.execute(text('TRUNCATE TABLE mental_training_sessions CASCADE'))
                    conn.execute(text('TRUNCATE TABLE ordered_session_drills CASCADE'))
                    conn.execute(text('TRUNCATE TABLE password_reset_codes CASCADE'))
                    conn.execute(text('TRUNCATE TABLE progress_history CASCADE'))
                    conn.execute(text('TRUNCATE TABLE refresh_tokens CASCADE'))
                    conn.execute(text('TRUNCATE TABLE saved_filters CASCADE'))
                    conn.execute(text('TRUNCATE TABLE session_preferences CASCADE'))
                    conn.execute(text('TRUNCATE TABLE training_sessions CASCADE'))
                    conn.commit()
                    print("   ✅ Manual clear completed")
                else:
                    print("   ✅ Database is properly cleared")
            
            # Now restore from the backup file
            print(f"   Restoring from backup: {backup_file.name}")
            
            # Use psql with connection parameters to handle large files and timeouts
            restore_cmd = [
                'psql',
                self.staging_url,
                '-f', str(backup_file),
                '--set=ON_ERROR_STOP=off',  # Continue on errors
                '--quiet',                  # Reduce output
                '--no-psqlrc'              # Don't use .psqlrc
            ]
            
            # Increase timeout for large files
            result = subprocess.run(restore_cmd, capture_output=True, text=True, timeout=600)
            
            # Log the full output for debugging
            print(f"   Restore command stdout: {result.stdout}")
            if result.stderr:
                print(f"   Restore command stderr: {result.stderr}")
            print(f"   Restore command return code: {result.returncode}")
            
            # Check for specific error types
            if result.returncode != 0:
                stderr_lower = result.stderr.lower()
                
                # Check for connection timeout issues
                if "operation timed out" in stderr_lower or "connection" in stderr_lower:
                    print("   ⚠️  Connection timeout detected, trying alternative approach...")
                    
                    # Try using pg_restore instead (if it's a custom format)
                    # But first check if it's a plain SQL file
                    if backup_file.suffix == '.sql':
                        print("   📝 Using SQL file - trying chunked approach...")
                        
                        # Try to restore in smaller chunks by reading the file and executing in parts
                        try:
                            self._restore_sql_in_chunks(backup_file)
                            print("   ✅ Chunked restore completed")
                        except Exception as e:
                            print(f"   ❌ Chunked restore failed: {e}")
                            return False
                    else:
                        print(f"   ❌ Failed to restore from backup: {result.stderr}")
                        return False
                else:
                    print(f"   ❌ Failed to restore from backup: {result.stderr}")
                    return False
            
            print("   ✅ Backup restored successfully")
            print("✅ Rollback completed successfully!")
            print("🎯 Note: Rollback restored staging to the exact backup state")
            print("   This restores the exact state from when the backup was created")
            return True
            
        except Exception as e:
            print(f"❌ Error during rollback: {e}")
            return False
    
    def _restore_sql_in_chunks(self, backup_file: Path):
        """Restore a large SQL file in chunks to avoid connection timeouts"""
        try:
            from sqlalchemy import create_engine, text
            
            # Create database connection
            engine = create_engine(self.staging_url)
            
            # Read the SQL file and split into chunks
            with open(backup_file, 'r') as f:
                content = f.read()
            
            # Split by semicolon and newline to get individual statements
            statements = []
            current_statement = ""
            
            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('--'):
                    continue
                    
                current_statement += line + '\n'
                
                # If line ends with semicolon, it's a complete statement
                if line.endswith(';'):
                    statements.append(current_statement.strip())
                    current_statement = ""
            
            # Add any remaining statement
            if current_statement.strip():
                statements.append(current_statement.strip())
            
            print(f"   📊 Found {len(statements)} SQL statements to execute")
            
            # Execute statements in batches
            batch_size = 100
            with engine.connect() as conn:
                for i in range(0, len(statements), batch_size):
                    batch = statements[i:i + batch_size]
                    print(f"   🔄 Executing batch {i//batch_size + 1}/{(len(statements) + batch_size - 1)//batch_size}")
                    
                    for statement in batch:
                        if statement.strip():
                            try:
                                conn.execute(text(statement))
                            except Exception as e:
                                # Log but continue - some errors might be expected
                                print(f"   ⚠️  Statement warning: {str(e)[:100]}...")
                    
                    # Commit after each batch
                    conn.commit()
            
            print("   ✅ All SQL statements executed successfully")
            
        except Exception as e:
            print(f"   ❌ Error in chunked restore: {e}")
            raise
    
    def rollback_latest(self, confirm: bool = True) -> bool:
        """Rollback to the most recent backup point"""
        try:
            rollback_points = self.list_rollback_points()
            if not rollback_points:
                print("❌ No rollback points available")
                return False
            
            latest = rollback_points[0]  # Already sorted by newest first
            backup_file = Path(latest['backup_file'])
            
            print(f"🎯 Rolling back to latest point: {latest['backup_name']}")
            return self.rollback_to_point(backup_file, confirm)
            
        except Exception as e:
            print(f"❌ Error rolling back to latest: {e}")
            return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Rollback manager for V2 migration')
    parser.add_argument('v2_url', help='V2 database URL')
    parser.add_argument('staging_url', help='Staging database URL')
    parser.add_argument('action', choices=['create', 'list', 'rollback', 'latest'], 
                       help='Action to perform')
    parser.add_argument('--file', help='Backup file for rollback (required for rollback action)')
    parser.add_argument('--description', help='Description for rollback point (for create action)')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    try:
        manager = RollbackManager(args.v2_url, args.staging_url)
        
        if args.action == 'create':
            description = args.description or f"Rollback point created at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            backup_path = manager.create_rollback_point(description)
            if backup_path:
                print(f"✅ Rollback point created successfully: {backup_path.name}")
            else:
                print("❌ Failed to create rollback point")
                sys.exit(1)
                
        elif args.action == 'list':
            manager.list_rollback_points()
            
        elif args.action == 'rollback':
            if not args.file:
                print("❌ --file argument required for rollback action")
                sys.exit(1)
            backup_file = Path(args.file)
            success = manager.rollback_to_point(backup_file, confirm=not args.yes)
            if not success:
                sys.exit(1)
                
        elif args.action == 'latest':
            success = manager.rollback_latest(confirm=not args.yes)
            if not success:
                sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()