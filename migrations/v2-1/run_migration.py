"""
run_migration.py
Main orchestration script that coordinates the entire migration process
"""

import sys
import os
import argparse
from pathlib import Path
import logging
from datetime import datetime

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))
from migration_config import config
from schema_sync import SchemaSync
from staging_setup import StagingSetup
from v2_migration_manager import V2MigrationManager
from test_migration import MigrationTester
from rollback_manager import RollbackManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(config.get_log_path("migration_runner")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MigrationRunner:
    """Main orchestration class for the migration process"""
    
    def __init__(self, v1_url: str, v2_url: str, staging_url: str):
        self.v1_url = v1_url
        self.v2_url = v2_url
        self.staging_url = staging_url
        
        self.rollback_manager = RollbackManager(v2_url, staging_url)
        self.rollback_point = None
    
    def check_status(self) -> bool:
        """Check the current status of databases and migration readiness"""
        try:
            logger.info("Checking migration status...")
            
            # Validate configuration
            if not config.validate():
                logger.error("❌ Configuration validation failed")
                return False
            
            # Check database connectivity
            if not self._check_database_connectivity():
                logger.error("❌ Database connectivity check failed")
                return False
            
            # Check schema synchronization
            if not self._check_schema_sync():
                logger.error("❌ Schema synchronization check failed")
                return False
            
            # Show user counts
            self._show_user_counts()
            
            logger.info("✅ Migration status check passed")
            return True
            
        except Exception as e:
            logger.error(f"Error checking migration status: {e}")
            return False
    
    def _check_database_connectivity(self) -> bool:
        """Check that all databases are accessible"""
        try:
            from sqlalchemy import create_engine, text
            
            databases = {
                'V1': self.v1_url,
                'V2': self.v2_url,
                'Staging': self.staging_url
            }
            
            for name, url in databases.items():
                try:
                    engine = create_engine(url)
                    with engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                    logger.info(f"✅ {name} database: Connected")
                except Exception as e:
                    logger.error(f"❌ {name} database: Connection failed - {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking database connectivity: {e}")
            return False
    
    def _check_schema_sync(self) -> bool:
        """Check if staging schema is synchronized with V2"""
        try:
            sync = SchemaSync(self.v2_url, self.staging_url)
            return sync.validate_schema_sync()
        except Exception as e:
            logger.error(f"Error checking schema sync: {e}")
            return False
    
    def _show_user_counts(self):
        """Show user counts in each database"""
        try:
            from sqlalchemy import create_engine, text
            
            databases = {
                'V1': self.v1_url,
                'V2': self.v2_url,
                'Staging': self.staging_url
            }
            
            logger.info("User counts:")
            for name, url in databases.items():
                try:
                    engine = create_engine(url)
                    with engine.connect() as conn:
                        count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
                        logger.info(f"  {name}: {count} users")
                except Exception as e:
                    logger.warning(f"  {name}: Unable to get user count - {e}")
                    
        except Exception as e:
            logger.error(f"Error showing user counts: {e}")
    
    def run_migration(self, skip_staging: bool = False, skip_tests: bool = False) -> bool:
        """Run the complete migration process"""
        try:
            logger.info("Starting V2 migration process...")
            
            # Step 1: Check status
            if not self.check_status():
                logger.error("Status check failed - aborting migration")
                return False
            
            # Step 2: Create rollback point
            logger.info("Creating rollback point...")
            self.rollback_point = self.rollback_manager.create_rollback_point()
            if not self.rollback_point:
                logger.error("Failed to create rollback point - aborting migration")
                return False
            
            # Step 3: Sync schemas
            if not skip_staging:
                logger.info("Synchronizing schemas...")
                sync = SchemaSync(self.v2_url, self.staging_url)
                if not sync.sync_schema():
                    logger.error("Schema synchronization failed - aborting migration")
                    return False
            
            # Step 4: Set up staging
            if not skip_staging:
                logger.info("Setting up staging database...")
                setup = StagingSetup(self.v2_url, self.staging_url)
                if not setup.setup_staging():
                    logger.error("Staging setup failed - aborting migration")
                    return False
            
            # Step 5: Run migration
            logger.info("Running migration...")
            migration_target = self.staging_url if not skip_staging else self.v2_url
            manager = V2MigrationManager(self.v1_url, migration_target)
            if not manager.run_migration():
                logger.error("Migration failed - initiating rollback")
                self._rollback_migration()
                return False
            
            # Step 6: Run tests
            if not skip_tests and not skip_staging:
                logger.info("Running migration tests...")
                tester = MigrationTester(self.v1_url, self.v2_url, self.staging_url)
                if not tester.run_all_tests():
                    logger.error("Migration tests failed - initiating rollback")
                    self._rollback_migration()
                    return False
            
            logger.info("✅ V2 migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            if self.rollback_point:
                logger.info("Initiating rollback due to error...")
                self._rollback_migration()
            return False
    
    def test_migration(self) -> bool:
        """Test migration on staging database (simplified - staging already has V2 data)"""
        try:
            logger.info("Running simplified migration test...")
            
            # Check status
            if not self.check_status():
                logger.error("Status check failed - aborting test")
                return False
            
            # Skip staging setup since V2 data is already in staging
            logger.info("Skipping staging setup - V2 data already present")
            
            # Run migration on staging
            logger.info("Running migration on staging...")
            manager = V2MigrationManager(self.v1_url, self.staging_url)
            if not manager.run_migration():
                logger.error("Migration test failed")
                return False
            
            logger.info("✅ Simplified migration test completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration test failed: {e}")
            return False
    
    def _rollback_migration(self):
        """Rollback migration using the rollback point"""
        try:
            if self.rollback_point and self.rollback_point.exists():
                logger.info(f"Rolling back migration using: {self.rollback_point}")
                if self.rollback_manager.rollback_migration(self.rollback_point):
                    logger.info("✅ Rollback completed successfully")
                else:
                    logger.error("❌ Rollback failed")
            else:
                logger.error("No rollback point available")
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
    
    def rollback_migration(self, rollback_file: Path) -> bool:
        """Manually rollback migration using specified rollback file"""
        try:
            logger.info(f"Rolling back migration using: {rollback_file}")
            
            if not rollback_file.exists():
                logger.error(f"Rollback file not found: {rollback_file}")
                return False
            
            if self.rollback_manager.rollback_migration(rollback_file):
                logger.info("✅ Rollback completed successfully")
                return True
            else:
                logger.error("❌ Rollback failed")
                return False
                
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            return False

def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(description="V2 Migration Runner")
    parser.add_argument("v1_url", help="V1 database URL")
    parser.add_argument("v2_url", help="V2 database URL")
    parser.add_argument("staging_url", help="Staging database URL")
    parser.add_argument("command", choices=["status", "migrate", "test", "rollback"], 
                       help="Command to execute")
    parser.add_argument("--skip-staging", action="store_true", 
                       help="Skip staging setup (run directly on V2)")
    parser.add_argument("--skip-tests", action="store_true", 
                       help="Skip testing phase")
    parser.add_argument("--rollback-file", type=Path, 
                       help="Rollback file path (for rollback command)")
    
    args = parser.parse_args()
    
    # Validate configuration
    if not config.validate():
        logger.error("Configuration validation failed")
        sys.exit(1)
    
    runner = MigrationRunner(args.v1_url, args.v2_url, args.staging_url)
    
    if args.command == "status":
        if runner.check_status():
            logger.info("Status check completed successfully")
            sys.exit(0)
        else:
            logger.error("Status check failed")
            sys.exit(1)
    
    elif args.command == "migrate":
        if runner.run_migration(skip_staging=args.skip_staging, skip_tests=args.skip_tests):
            logger.info("Migration completed successfully")
            sys.exit(0)
        else:
            logger.error("Migration failed")
            sys.exit(1)
    
    elif args.command == "test":
        if runner.test_migration():
            logger.info("Migration test completed successfully")
            sys.exit(0)
        else:
            logger.error("Migration test failed")
            sys.exit(1)
    
    elif args.command == "rollback":
        if not args.rollback_file:
            logger.error("Rollback command requires --rollback-file argument")
            sys.exit(1)
        
        if runner.rollback_migration(args.rollback_file):
            logger.info("Rollback completed successfully")
            sys.exit(0)
        else:
            logger.error("Rollback failed")
            sys.exit(1)

if __name__ == "__main__":
    main()
