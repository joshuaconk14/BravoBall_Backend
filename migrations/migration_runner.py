#!/usr/bin/env python3
"""
Migration Runner - BravoBall Backend
Utility script to manage database migrations

Usage:
    python migration_runner.py --list
    python migration_runner.py --list --version v2-1
    python migration_runner.py --run MIGRATION_NAME
    python migration_runner.py --run MIGRATION_NAME --dry-run --version v2-1
    python migration_runner.py --verify MIGRATION_NAME --version v2-1
"""

import os
import sys
import glob
import importlib.util
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MigrationRunner:
    def __init__(self, migrations_dir=None, version=None):
        """Initialize the migration runner"""
        self.migrations_dir = migrations_dir or Path(__file__).parent
        self.version = version
        self.available_migrations = self._discover_migrations()
    
    def _discover_migrations(self):
        """Discover all migration files in the migrations directory"""
        migrations = []
        
        if self.version:
            # Look for migrations in a specific version folder
            version_dir = os.path.join(self.migrations_dir, self.version)
            if os.path.exists(version_dir):
                migration_pattern = os.path.join(version_dir, "20*_*.py")
                migration_files = glob.glob(migration_pattern)
                
                for file_path in sorted(migration_files):
                    filename = os.path.basename(file_path)
                    migration_name = filename.replace('.py', '')
                    migrations.append({
                        'name': migration_name,
                        'file_path': file_path,
                        'filename': filename,
                        'version': self.version
                    })
        else:
            # Look for migrations in both main directory and version folders
            # Main directory
            migration_pattern = os.path.join(self.migrations_dir, "20*_*.py")
            migration_files = glob.glob(migration_pattern)
            
            for file_path in sorted(migration_files):
                filename = os.path.basename(file_path)
                if filename != "migration_runner.py":  # Exclude this runner script
                    migration_name = filename.replace('.py', '')
                    migrations.append({
                        'name': migration_name,
                        'file_path': file_path,
                        'filename': filename,
                        'version': 'main'
                    })
            
            # Version directories
            for item in os.listdir(self.migrations_dir):
                item_path = os.path.join(self.migrations_dir, item)
                if os.path.isdir(item_path) and item.startswith('v') and not item.startswith('__'):
                    version_pattern = os.path.join(item_path, "20*_*.py")
                    version_files = glob.glob(version_pattern)
                    
                    for file_path in sorted(version_files):
                        filename = os.path.basename(file_path)
                        migration_name = filename.replace('.py', '')
                        migrations.append({
                            'name': migration_name,
                            'file_path': file_path,
                            'filename': filename,
                            'version': item
                        })
        
        return migrations
    
    def list_migrations(self):
        """List all available migrations"""
        if self.version:
            logger.info(f"📋 Available Migrations for Version {self.version}:")
        else:
            logger.info("📋 Available Migrations (All Versions):")
        logger.info("=" * 60)
        
        if not self.available_migrations:
            logger.info("No migrations found.")
            return
        
        # Group by version
        versions = {}
        for migration in self.available_migrations:
            version = migration['version']
            if version not in versions:
                versions[version] = []
            versions[version].append(migration)
        
        for version in sorted(versions.keys()):
            if not self.version:  # Only show version headers when listing all
                logger.info(f"\n📦 Version: {version}")
                logger.info("-" * 30)
            
            for migration in versions[version]:
                logger.info(f"📄 {migration['name']}")
                
                # Try to extract description from migration docstring
                try:
                    spec = importlib.util.spec_from_file_location("migration", migration['file_path'])
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if module.__doc__:
                        # Extract first line of docstring for description
                        lines = module.__doc__.strip().split('\n')
                        for line in lines[1:6]:  # Look at first few lines
                            if line.strip().startswith('Purpose:'):
                                description = line.strip().replace('Purpose:', '').strip()
                                logger.info(f"   📝 {description}")
                                break
                        else:
                            # Fallback to first line
                            description = lines[0]
                            logger.info(f"   📝 {description}")
                    
                except Exception:
                    logger.info("   📝 (No description available)")
                
                logger.info("")
    
    def run_migration(self, migration_name, dry_run=False, database_url=None):
        """Run a specific migration"""
        migration = self._find_migration(migration_name)
        if not migration:
            logger.error(f"❌ Migration '{migration_name}' not found")
            if self.version:
                logger.info(f"   Looking in version: {self.version}")
            else:
                logger.info("   Searched all versions")
            return False
        
        logger.info(f"🚀 Running migration: {migration['name']}")
        logger.info(f"📦 Version: {migration['version']}")
        logger.info(f"📁 File: {migration['filename']}")
        logger.info(f"🔄 Dry run: {dry_run}")
        
        try:
            # Import and run the migration
            spec = importlib.util.spec_from_file_location("migration", migration['file_path'])
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check if the migration has the expected structure
            if not hasattr(module, 'main'):
                logger.error(f"❌ Migration {migration['name']} does not have a main() function")
                return False
            
            # Prepare arguments for the migration
            original_argv = sys.argv.copy()
            sys.argv = [migration['file_path']]
            
            if dry_run:
                sys.argv.append('--dry-run')
            
            if database_url:
                sys.argv.extend(['--database-url', database_url])
            
            # Run the migration
            module.main()
            
            # Restore original argv
            sys.argv = original_argv
            
            logger.info(f"✅ Migration {migration['name']} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration {migration['name']} failed: {str(e)}")
            return False
    
    def verify_migration(self, migration_name):
        """Verify that a migration was applied successfully"""
        migration = self._find_migration(migration_name)
        if not migration:
            logger.error(f"❌ Migration '{migration_name}' not found")
            return False
        
        logger.info(f"🔍 Verifying migration: {migration['name']}")
        
        try:
            # Import the migration module
            spec = importlib.util.spec_from_file_location("migration", migration['file_path'])
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for migrator class (try common names)
            migrator_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    hasattr(attr, 'verify_migration') and 
                    attr_name.endswith('Migrator')):
                    migrator_class = attr
                    break
            
            if migrator_class:
                migrator = migrator_class()
                result = migrator.verify_migration()
                
                if result:
                    logger.info(f"✅ Migration {migration['name']} verification passed")
                else:
                    logger.error(f"❌ Migration {migration['name']} verification failed")
                
                return result
            else:
                logger.warning(f"⚠️ Migration {migration['name']} does not have verification method")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error verifying migration {migration['name']}: {str(e)}")
            return False
    
    def get_migration_status(self):
        """Get the status of all migrations"""
        if self.version:
            logger.info(f"📊 Migration Status for Version {self.version}:")
        else:
            logger.info("📊 Migration Status (All Versions):")
        logger.info("=" * 60)
        
        # Group by version
        versions = {}
        for migration in self.available_migrations:
            version = migration['version']
            if version not in versions:
                versions[version] = []
            versions[version].append(migration)
        
        for version in sorted(versions.keys()):
            if not self.version:
                logger.info(f"\n📦 Version: {version}")
                logger.info("-" * 30)
            
            for migration in versions[version]:
                logger.info(f"📄 {migration['name']}")
                
                # Check migration directory for logs
                migration_dir = os.path.dirname(migration['file_path'])
                log_pattern = os.path.join(migration_dir, "migration_log_*.log")
                log_files = glob.glob(log_pattern)
                
                if log_files:
                    latest_log = max(log_files, key=os.path.getctime)
                    log_time = datetime.fromtimestamp(os.path.getctime(latest_log))
                    logger.info(f"   📅 Last run: {log_time.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    logger.info(f"   📅 Status: Not run")
                
                # Check for backup files
                backup_pattern = os.path.join(migration_dir, "*backup*.sql")
                backup_files = glob.glob(backup_pattern)
                
                if backup_files:
                    logger.info(f"   💾 Backups: {len(backup_files)} files")
                
                logger.info("")
    
    def _find_migration(self, migration_name):
        """Find a migration by name"""
        for migration in self.available_migrations:
            if (migration['name'] == migration_name or 
                migration['name'].endswith(migration_name) or
                migration_name in migration['name']):
                return migration
        return None

def main():
    """Main entry point for migration runner"""
    parser = argparse.ArgumentParser(description='BravoBall Migration Runner')
    parser.add_argument('--list', action='store_true', help='List all available migrations')
    parser.add_argument('--run', help='Run a specific migration')
    parser.add_argument('--verify', help='Verify a specific migration')
    parser.add_argument('--status', action='store_true', help='Show migration status')
    parser.add_argument('--dry-run', action='store_true', help='Run migration in dry-run mode')
    parser.add_argument('--database-url', help='Database URL (overrides environment variable)')
    parser.add_argument('--version', help='Target specific version folder (e.g., v2-1)')
    
    args = parser.parse_args()
    
    # Create migration runner
    runner = MigrationRunner(version=args.version)
    
    try:
        if args.list:
            runner.list_migrations()
        
        elif args.run:
            success = runner.run_migration(args.run, dry_run=args.dry_run, database_url=args.database_url)
            sys.exit(0 if success else 1)
        
        elif args.verify:
            success = runner.verify_migration(args.verify)
            sys.exit(0 if success else 1)
        
        elif args.status:
            runner.get_migration_status()
        
        else:
            parser.print_help()
            logger.info("\n💡 Quick start:")
            logger.info("   python migration_runner.py --list")
            logger.info("   python migration_runner.py --list --version v2-1")
            logger.info("   python migration_runner.py --run MIGRATION_NAME --version v2-1 --dry-run")
            
    except KeyboardInterrupt:
        logger.info("\n⚠️ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Migration runner error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 