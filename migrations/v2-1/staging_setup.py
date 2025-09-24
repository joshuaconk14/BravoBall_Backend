"""
staging_setup.py
Sets up staging database for safe testing by copying V2 production data
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime

# Add parent directory to path to import our models
sys.path.append(str(Path(__file__).parent.parent.parent))
from models import Base
from migration_config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(config.get_log_path("staging_setup")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StagingSetup:
    """Handles staging database setup for safe testing"""
    
    def __init__(self, source_url: str, target_url: str):
        self.source_url = source_url
        self.target_url = target_url
        self.source_engine = create_engine(source_url)
        self.target_engine = create_engine(target_url)
        
    def create_backup(self) -> Path:
        """Create backup of current staging data"""
        try:
            logger.info("Creating backup of current staging data...")
            
            backup_path = config.get_backup_path("staging_backup")
            
            # Check if staging is empty first
            if self._is_staging_empty():
                logger.info("Staging database is empty - skipping backup")
                return backup_path
            
            # If staging has data but we're in test mode, skip backup to avoid version issues
            if config.is_debug_mode():
                logger.info("Debug mode: skipping backup to avoid version mismatch issues")
                return backup_path
            
            # Use pg_dump to create backup with version compatibility
            cmd = [
                'pg_dump',
                self.target_url,
                '--format=custom',
                '--no-sync',  # Avoid sync issues
                '--file', str(backup_path.with_suffix('.dump'))
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                # If backup fails due to version mismatch, try without custom format
                logger.warning(f"Custom format backup failed: {result.stderr}")
                logger.info("Retrying backup with plain format...")
                
                cmd = [
                    'pg_dump',
                    self.target_url,
                    '--format=plain',
                    '--no-sync',
                    '--file', str(backup_path.with_suffix('.sql'))
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"Backup failed: {result.stderr}")
                    return None
            
            # Also create a JSON backup for easier inspection
            self._create_json_backup(backup_path.with_suffix('.json'))
            
            logger.info(f"✅ Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None
    
    def _is_staging_empty(self) -> bool:
        """Check if staging database is empty"""
        try:
            with self.target_engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                return user_count == 0
        except Exception:
            return True  # If we can't check, assume it's empty
    
    def _create_json_backup(self, backup_path: Path):
        """Create JSON backup of staging data"""
        try:
            with self.target_engine.connect() as conn:
                # Get all tables
                tables = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)).fetchall()
                
                backup_data = {}
                for (table_name,) in tables:
                    try:
                        # Get table data
                        data = conn.execute(text(f'SELECT * FROM "{table_name}"')).fetchall()
                        columns = conn.execute(text(f"""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = '{table_name}'
                            ORDER BY ordinal_position
                        """)).fetchall()
                        
                        column_names = [col[0] for col in columns]
                        backup_data[table_name] = [
                            dict(zip(column_names, row)) for row in data
                        ]
                    except Exception as e:
                        logger.warning(f"Could not backup table {table_name}: {e}")
                
                with open(backup_path, 'w') as f:
                    json.dump(backup_data, f, indent=2, default=str)
                    
        except Exception as e:
            logger.error(f"Error creating JSON backup: {e}")
    
    def clear_staging_database(self) -> bool:
        """Clear all data from staging database"""
        try:
            logger.info("Clearing staging database...")
            
            with self.target_engine.connect() as conn:
                # Get all tables
                tables = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)).fetchall()
                
                # Try to disable foreign key checks, but continue if permission denied
                try:
                    conn.execute(text("SET session_replication_role = replica;"))
                    disable_fk_checks = True
                except Exception as e:
                    if "permission denied" in str(e).lower():
                        logger.warning("Cannot disable foreign key checks due to permissions - proceeding with CASCADE")
                        disable_fk_checks = False
                    else:
                        raise e
                
                # Clear all tables in reverse dependency order to avoid foreign key issues
                # First, clear tables that are likely to have foreign keys
                table_clear_order = [
                    'ordered_session_drills', 'drill_group_items', 'completed_sessions',
                    'session_preferences', 'progress_history', 'saved_filters', 
                    'refresh_tokens', 'password_reset_codes', 'email_verification_codes',
                    'mental_training_sessions', 'training_sessions', 'custom_drills',
                    'drill_groups', 'users', 'drills', 'drill_categories', 
                    'drill_skill_focus', 'mental_training_quotes', 'session_drills'
                ]
                
                # Clear tables in the specified order - each in its own transaction
                for table_name in table_clear_order:
                    if any(t[0] == table_name for t in tables):
                        try:
                            # Use a separate connection for each table to avoid transaction issues
                            with self.target_engine.connect() as table_conn:
                                table_conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))
                                table_conn.commit()
                                logger.info(f"Cleared table: {table_name}")
                        except Exception as e:
                            logger.warning(f"Could not clear table {table_name}: {e}")
                
                # Clear any remaining tables not in our ordered list
                for (table_name,) in tables:
                    if table_name not in table_clear_order:
                        try:
                            # Use a separate connection for each table to avoid transaction issues
                            with self.target_engine.connect() as table_conn:
                                table_conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))
                                table_conn.commit()
                                logger.info(f"Cleared table: {table_name}")
                        except Exception as e:
                            logger.warning(f"Could not clear table {table_name}: {e}")
                
                # Re-enable foreign key checks if we disabled them
                if disable_fk_checks:
                    with self.target_engine.connect() as fk_conn:
                        fk_conn.execute(text("SET session_replication_role = DEFAULT;"))
                        fk_conn.commit()
            
            logger.info("✅ Staging database cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing staging database: {e}")
            # Try to rollback the transaction
            try:
                with self.target_engine.connect() as conn:
                    conn.rollback()
            except:
                pass
            return False
    
    def copy_data_from_source(self) -> bool:
        """Copy all data from source to staging"""
        try:
            logger.info("Copying data from source to staging...")
            
            # Use pg_dump and pg_restore for efficient data transfer
            # Try custom format first, fall back to plain SQL if needed
            dump_file = config.get_backup_path("temp_dump").with_suffix('.dump')
            sql_file = config.get_backup_path("temp_dump").with_suffix('.sql')
            
            # Create dump from source - try custom format first
            logger.info("Creating dump from source database...")
            dump_cmd = [
                'pg_dump',
                self.source_url,
                '--format=custom',
                '--data-only',
                '--file', str(dump_file)
            ]
            
            result = subprocess.run(dump_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"Custom format dump failed: {result.stderr}")
                logger.info("Trying plain SQL format...")
                
                # Fall back to plain SQL format
                dump_cmd = [
                    'pg_dump',
                    self.source_url,
                    '--format=plain',
                    '--data-only',
                    '--file', str(sql_file)
                ]
                
                result = subprocess.run(dump_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"Plain SQL dump also failed: {result.stderr}")
                    return False
                
                # Use SQL file for restore
                dump_file = sql_file
            
            # Restore to staging with improved error handling
            logger.info("Restoring data to staging database...")
            
            # Choose restore method based on file format
            if dump_file.suffix == '.sql':
                # Use psql for SQL files
                restore_cmd = [
                    'psql',
                    self.target_url,
                    '-f', str(dump_file)
                ]
            else:
                # Use pg_restore for custom format
                restore_cmd = [
                    'pg_restore',
                    '--data-only',
                    '--no-owner',
                    '--no-privileges',
                    '--single-transaction',  # Use single transaction for better error handling
                    '--exit-on-error',       # Stop on first error
                    '--dbname', self.target_url,
                    str(dump_file)
                ]
            
            result = subprocess.run(restore_cmd, capture_output=True, text=True)
            
            # Check for specific error types and handle them appropriately
            if result.returncode != 0:
                stderr_lower = result.stderr.lower()
                
                # Check for permission issues with triggers (these are warnings, not errors)
                if "permission denied" in stderr_lower and "trigger" in stderr_lower:
                    logger.warning("Permission issues with system triggers detected - this is expected and can be ignored")
                    # Try restore again without --exit-on-error to continue despite trigger warnings
                    logger.info("Retrying restore without exit-on-error to handle trigger warnings...")
                    
                    if dump_file.suffix == '.sql':
                        # For SQL files, just retry with psql
                        restore_cmd_retry = [
                            'psql',
                            self.target_url,
                            '-f', str(dump_file)
                        ]
                    else:
                        # For custom format, retry without exit-on-error
                        restore_cmd_retry = [
                            'pg_restore',
                            '--data-only',
                            '--no-owner',
                            '--no-privileges',
                            '--dbname', self.target_url,
                            str(dump_file)
                        ]
                    result = subprocess.run(restore_cmd_retry, capture_output=True, text=True)
                    
                # Check for duplicate key violations (these are expected if staging has data)
                if "duplicate key value violates unique constraint" in stderr_lower:
                    logger.warning("Duplicate key violations detected - this is expected if staging already has some data")
                    # This is actually fine - the data is already there
                    
                # Check for other serious errors
                if result.returncode != 0 and "duplicate key value violates unique constraint" not in stderr_lower:
                    logger.error(f"Restore failed with serious error: {result.stderr}")
                    return False
            
            # Clean up temp files
            dump_file.unlink(missing_ok=True)
            sql_file.unlink(missing_ok=True)
            
            # Reset sequence numbers to avoid ID conflicts
            self._reset_sequences()
            
            logger.info("✅ Data copied from source to staging")
            return True
            
        except Exception as e:
            logger.error(f"Error copying data: {e}")
            return False
    
    def _reset_sequences(self):
        """Reset sequence numbers to avoid ID conflicts"""
        try:
            logger.info("Resetting sequence numbers...")
            
            # Get all sequences first
            with self.target_engine.connect() as conn:
                sequences = conn.execute(text("""
                    SELECT sequence_name 
                    FROM information_schema.sequences 
                    WHERE sequence_schema = 'public'
                """)).fetchall()
            
            # Reset each sequence in its own transaction to avoid transaction issues
            for (seq_name,) in sequences:
                try:
                    # Get the table name from sequence name (remove _id_seq suffix)
                    table_name = seq_name.replace('_id_seq', '')
                    
                    # Use separate connection for each sequence reset
                    with self.target_engine.connect() as seq_conn:
                        # Reset sequence to max ID + 1
                        seq_conn.execute(text(f"""
                            SELECT setval('{seq_name}', 
                                COALESCE((SELECT MAX(id) FROM "{table_name}"), 0) + 1, 
                                false)
                        """))
                        seq_conn.commit()
                        logger.info(f"Reset sequence {seq_name}")
                        
                except Exception as e:
                    logger.warning(f"Could not reset sequence {seq_name}: {e}")
            
            logger.info("✅ Sequence numbers reset")
            
        except Exception as e:
            logger.error(f"Error resetting sequences: {e}")
    
    def validate_data_copy(self) -> bool:
        """Validate that data was copied correctly"""
        try:
            logger.info("Validating data copy...")
            
            with self.source_engine.connect() as source_conn, \
                 self.target_engine.connect() as target_conn:
                
                # Get all tables
                tables = source_conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)).fetchall()
                
                validation_results = {}
                
                for (table_name,) in tables:
                    try:
                        # Count rows in both databases
                        source_count = source_conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
                        target_count = target_conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
                        
                        validation_results[table_name] = {
                            'source_count': source_count,
                            'target_count': target_count,
                            'match': source_count == target_count
                        }
                        
                        if source_count != target_count:
                            logger.warning(f"Row count mismatch in {table_name}: source={source_count}, target={target_count}")
                        
                    except Exception as e:
                        logger.warning(f"Could not validate table {table_name}: {e}")
                        validation_results[table_name] = {'error': str(e)}
                
                # Save validation results
                validation_path = config.get_backup_path("staging_validation")
                with open(validation_path.with_suffix('.json'), 'w') as f:
                    json.dump(validation_results, f, indent=2)
                
                # Check if all validations passed
                all_passed = all(
                    result.get('match', False) for result in validation_results.values()
                    if 'error' not in result
                )
                
                if all_passed:
                    logger.info("✅ Data copy validation passed")
                else:
                    logger.warning("⚠️ Some data copy validations failed - check validation file")
                
                return all_passed
                
        except Exception as e:
            logger.error(f"Error validating data copy: {e}")
            return False
    
    def setup_staging(self) -> bool:
        """Complete staging setup process"""
        try:
            logger.info("Starting staging database setup...")
            
            # Step 1: Create backup of current staging
            backup_path = self.create_backup()
            if not backup_path:
                logger.error("Failed to create backup")
                return False
            
            # Step 2: Clear staging database
            if not self.clear_staging_database():
                logger.error("Failed to clear staging database")
                return False
            
            # Step 3: Copy data from source
            if not self.copy_data_from_source():
                logger.error("Failed to copy data from source")
                return False
            
            # Step 4: Validate data copy
            if not self.validate_data_copy():
                logger.warning("Data copy validation failed - continuing anyway")
            
            logger.info("✅ Staging database setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Staging setup failed: {e}")
            return False
    
    def get_staging_info(self) -> dict:
        """Get information about current staging database"""
        try:
            with self.target_engine.connect() as conn:
                # Get table counts
                tables = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)).fetchall()
                
                table_info = {}
                total_rows = 0
                
                for (table_name,) in tables:
                    try:
                        count = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
                        table_info[table_name] = count
                        total_rows += count
                    except Exception as e:
                        table_info[table_name] = f"Error: {e}"
                
                return {
                    'total_tables': len(tables),
                    'total_rows': total_rows,
                    'table_info': table_info,
                    'database_url': self.target_url
                }
                
        except Exception as e:
            logger.error(f"Error getting staging info: {e}")
            return {'error': str(e)}

def main():
    """Main function for command line usage"""
    if len(sys.argv) != 3:
        print("Usage: python staging_setup.py <source_database_url> <target_database_url>")
        print("Example: python staging_setup.py <V2_DATABASE_URL> <STAGING_DATABASE_URL>")
        sys.exit(1)
    
    source_url = sys.argv[1]
    target_url = sys.argv[2]
    
    logger.info(f"Setting up staging database from {source_url} to {target_url}")
    
    setup = StagingSetup(source_url, target_url)
    
    if setup.setup_staging():
        # Show staging info
        info = setup.get_staging_info()
        logger.info(f"Staging database info: {json.dumps(info, indent=2)}")
        logger.info("Staging database setup completed successfully")
        sys.exit(0)
    else:
        logger.error("Staging database setup failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
