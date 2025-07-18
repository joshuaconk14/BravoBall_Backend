#!/usr/bin/env python3
"""
production_migration_plan.py
Comprehensive production migration plan for drill skill focus UUID migration.

This script provides a complete plan for safely migrating from drill_id to drill_uuid
relationships in production with full backup and rollback capabilities.

Usage:
    python production_migration_plan.py backup <DATABASE_URL>        # Create full backup
    python production_migration_plan.py validate <DATABASE_URL>      # Validate current state
    python production_migration_plan.py migrate <DATABASE_URL>       # Run full migration
    python production_migration_plan.py test <DATABASE_URL>          # Test API endpoints
    python production_migration_plan.py rollback <DATABASE_URL>      # Emergency rollback
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
import models
from config import get_logger
import subprocess
import urllib.parse

logger = get_logger(__name__)

class ProductionMigrator:
    def __init__(self, database_url):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = SessionLocal()
        
        # Parse database info for backup commands
        parsed_url = urllib.parse.urlparse(database_url)
        self.db_name = parsed_url.path[1:]  # Remove leading slash
        self.db_host = parsed_url.hostname
        self.db_port = parsed_url.port or 5432
        self.db_user = parsed_url.username
        self.db_password = parsed_url.password
        
        # Backup file naming
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_file = f"bravoball_backup_{self.db_name}_{timestamp}.sql"
        
    def create_full_backup(self):
        """Create a complete database backup before migration"""
        logger.info("💾 CREATING PRODUCTION BACKUP")
        logger.info("=" * 50)
        
        # Set PGPASSWORD environment variable if password exists
        env = os.environ.copy()
        if self.db_password:
            env['PGPASSWORD'] = self.db_password
        
        # Build pg_dump command
        dump_cmd = [
            'pg_dump',
            '-h', str(self.db_host),
            '-p', str(self.db_port),
            '-U', self.db_user,
            '-v',  # Verbose
            '--clean',  # Include DROP statements
            '--if-exists',  # Don't error if objects don't exist
            '--format=custom',  # Custom format for better compression
            self.db_name
        ]
        
        try:
            logger.info(f"Creating backup: {self.backup_file}")
            logger.info(f"Command: {' '.join(dump_cmd)} > {self.backup_file}")
            
            with open(self.backup_file, 'wb') as backup_file:
                result = subprocess.run(
                    dump_cmd, 
                    stdout=backup_file, 
                    stderr=subprocess.PIPE,
                    env=env,
                    check=True
                )
            
            # Verify backup file exists and has content
            backup_path = Path(self.backup_file)
            if backup_path.exists() and backup_path.stat().st_size > 0:
                size_mb = backup_path.stat().st_size / (1024 * 1024)
                logger.info(f"✅ Backup created successfully: {self.backup_file} ({size_mb:.1f} MB)")
                return True
            else:
                logger.error("❌ Backup file is empty or doesn't exist")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Backup failed: {e}")
            logger.error(f"stderr: {e.stderr.decode() if e.stderr else 'No error output'}")
            return False
        except Exception as e:
            logger.error(f"❌ Backup failed with exception: {e}")
            return False
    
    def validate_current_state(self):
        """Validate the current database state before migration"""
        logger.info("🔍 VALIDATING CURRENT DATABASE STATE")
        logger.info("=" * 50)
        
        validation_results = {
            'total_drills': 0,
            'total_custom_drills': 0,
            'total_skill_focus': 0,
            'drills_without_skills': 0,
            'api_test_results': {},
            'issues': []
        }
        
        try:
            # Count drills
            validation_results['total_drills'] = self.db.query(models.Drill).count()
            validation_results['total_custom_drills'] = self.db.query(models.CustomDrill).count()
            validation_results['total_skill_focus'] = self.db.query(models.DrillSkillFocus).count()
            
            # Count drills without skill focus
            query = text("""
                SELECT COUNT(*)
                FROM drills d
                LEFT JOIN drill_skill_focus dsf ON d.uuid = dsf.drill_uuid
                WHERE dsf.drill_uuid IS NULL
            """)
            result = self.db.execute(query)
            validation_results['drills_without_skills'] = result.scalar()
            
            # Log results
            logger.info(f"📊 Total drills: {validation_results['total_drills']}")
            logger.info(f"📊 Total custom drills: {validation_results['total_custom_drills']}")
            logger.info(f"📊 Total skill focus entries: {validation_results['total_skill_focus']}")
            logger.info(f"⚠️  Drills without skill focus: {validation_results['drills_without_skills']}")
            
            # Check for issues
            if validation_results['drills_without_skills'] > 0:
                validation_results['issues'].append(
                    f"{validation_results['drills_without_skills']} drills missing skill focus"
                )
            
            # Test sample API formatting
            sample_drill = self.db.query(models.Drill).first()
            if sample_drill:
                try:
                    from routers.router_utils import drill_to_response
                    api_response = drill_to_response(sample_drill, self.db)
                    
                    validation_results['api_test_results'] = {
                        'drill_title': sample_drill.title,
                        'has_primary_skill': bool(api_response.get('primary_skill')),
                        'primary_skill': api_response.get('primary_skill', {}),
                        'secondary_skills_count': len(api_response.get('secondary_skills', []))
                    }
                    
                    logger.info(f"🧪 API Test - Drill: '{sample_drill.title}'")
                    logger.info(f"   Primary skill: {api_response.get('primary_skill', 'None')}")
                    
                except ImportError:
                    validation_results['issues'].append("Could not import API formatting function")
            
            if validation_results['issues']:
                logger.warning("⚠️  Issues found:")
                for issue in validation_results['issues']:
                    logger.warning(f"   - {issue}")
            else:
                logger.info("✅ No issues found")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")
            return None
    
    def run_migration(self):
        """Run the complete migration process"""
        logger.info("🚀 STARTING PRODUCTION MIGRATION")
        logger.info("=" * 50)
        
        try:
            # Step 1: Run schema migration
            logger.info("Step 1: Running schema migration...")
            from migrate_schema import SchemaMigrator
            migrator = SchemaMigrator(self.database_url)
            migrator.run_migration(dry_run=False, seed_data=False)
            
            # Step 2: Fix drill skill focus
            logger.info("Step 2: Fixing drill skill focus entries...")
            self.fix_drill_skills()
            
            # Step 3: Validate migration
            logger.info("Step 3: Validating migration results...")
            validation = self.validate_current_state()
            
            if validation and validation['drills_without_skills'] == 0:
                logger.info("✅ Migration completed successfully!")
                return True
            else:
                logger.error("❌ Migration validation failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
    
    def fix_drill_skills(self):
        """Fix drills missing skill focus entries"""
        logger.info("🔧 Fixing drill skill focus entries...")
        
        # Find drills without skill focus
        query = text("""
            SELECT d.id, d.uuid, d.title, d.category_id
            FROM drills d
            LEFT JOIN drill_skill_focus dsf ON d.uuid = dsf.drill_uuid
            WHERE dsf.drill_uuid IS NULL
        """)
        
        result = self.db.execute(query)
        drills_without_skills = result.fetchall()
        
        if not drills_without_skills:
            logger.info("✅ All drills already have skill focus!")
            return 0
        
        logger.info(f"Found {len(drills_without_skills)} drills to fix")
        
        # Get category mapping
        categories = self.db.query(models.DrillCategory).all()
        category_map = {cat.id: cat.name for cat in categories}
        
        # Default skill mappings
        default_skills = {
            'shooting': {'category': 'shooting', 'sub_skill': 'finishing'},
            'passing': {'category': 'passing', 'sub_skill': 'short_passing'},
            'dribbling': {'category': 'dribbling', 'sub_skill': 'ball_mastery'},
            'first_touch': {'category': 'first_touch', 'sub_skill': 'ground_control'},
            'fitness': {'category': 'fitness', 'sub_skill': 'agility'},
            'defending': {'category': 'defending', 'sub_skill': 'positioning'},
        }
        
        fixed_count = 0
        for drill_data in drills_without_skills:
            drill_id, drill_uuid, drill_title, category_id = drill_data
            
            category_name = category_map.get(category_id, 'general').lower()
            
            if category_name in default_skills:
                skill_info = default_skills[category_name]
            else:
                skill_info = {'category': 'fitness', 'sub_skill': 'agility'}
            
            skill_focus = models.DrillSkillFocus(
                drill_uuid=drill_uuid,
                category=skill_info['category'],
                sub_skill=skill_info['sub_skill'],
                is_primary=True
            )
            
            self.db.add(skill_focus)
            fixed_count += 1
            
            if fixed_count % 10 == 0:  # Log progress every 10 fixes
                logger.info(f"   Fixed {fixed_count}/{len(drills_without_skills)} drills...")
        
        self.db.commit()
        logger.info(f"✅ Fixed {fixed_count} drills!")
        return fixed_count
    
    def test_api_endpoints(self):
        """Test API endpoints to ensure skill focus is working"""
        logger.info("🧪 TESTING API ENDPOINTS")
        logger.info("=" * 50)
        
        try:
            # Test drill formatting
            from routers.router_utils import drill_to_response
            
            # Get a sample of different drill types
            drill_categories = self.db.execute(text("""
                SELECT DISTINCT dc.name, d.id, d.uuid, d.title
                FROM drills d
                JOIN drill_categories dc ON d.category_id = dc.id
                LIMIT 5
            """)).fetchall()
            
            all_tests_passed = True
            
            for category_name, drill_id, drill_uuid, drill_title in drill_categories:
                logger.info(f"Testing {category_name} drill: '{drill_title}'")
                
                drill = self.db.query(models.Drill).filter(models.Drill.uuid == drill_uuid).first()
                if drill:
                    api_response = drill_to_response(drill, self.db)
                    
                    primary_skill = api_response.get('primary_skill', {})
                    if primary_skill and primary_skill.get('category') and primary_skill.get('sub_skill'):
                        logger.info(f"   ✅ Primary skill: {primary_skill['category']} -> {primary_skill['sub_skill']}")
                    else:
                        logger.error(f"   ❌ Missing or invalid primary skill: {primary_skill}")
                        all_tests_passed = False
                else:
                    logger.error(f"   ❌ Could not find drill with UUID: {drill_uuid}")
                    all_tests_passed = False
            
            if all_tests_passed:
                logger.info("✅ All API tests passed!")
            else:
                logger.error("❌ Some API tests failed!")
            
            return all_tests_passed
            
        except Exception as e:
            logger.error(f"❌ API testing failed: {e}")
            return False
    
    def emergency_rollback(self):
        """Emergency rollback procedure"""
        logger.info("🚨 EMERGENCY ROLLBACK PROCEDURE")
        logger.info("=" * 50)
        
        backup_path = Path(self.backup_file)
        if not backup_path.exists():
            logger.error(f"❌ Backup file not found: {self.backup_file}")
            logger.error("❌ Cannot perform automatic rollback!")
            logger.info("Manual rollback required:")
            logger.info("1. Restore from your manual backup")
            logger.info("2. Or contact your database administrator")
            return False
        
        logger.warning("⚠️  This will restore the database to the backup state!")
        logger.warning("⚠️  All changes since backup will be LOST!")
        
        response = input("Type 'ROLLBACK' to confirm emergency rollback: ")
        if response != 'ROLLBACK':
            logger.info("❌ Rollback cancelled")
            return False
        
        try:
            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            if self.db_password:
                env['PGPASSWORD'] = self.db_password
            
            # Build pg_restore command
            restore_cmd = [
                'pg_restore',
                '-h', str(self.db_host),
                '-p', str(self.db_port),
                '-U', self.db_user,
                '-d', self.db_name,
                '-v',  # Verbose
                '--clean',  # Clean database before restore
                '--if-exists',  # Don't error if objects don't exist
                self.backup_file
            ]
            
            logger.info(f"Restoring from backup: {self.backup_file}")
            
            result = subprocess.run(
                restore_cmd,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("✅ Emergency rollback completed successfully!")
                logger.info("Database restored to backup state")
                return True
            else:
                logger.error(f"❌ Rollback failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Rollback failed with exception: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        self.db.close()


def print_production_migration_guide():
    """Print comprehensive production migration guide"""
    print("""
🚀 PRODUCTION MIGRATION GUIDE
==============================

This migration fixes the drill skill focus relationships to ensure drills
show their proper categories instead of "general".

BEFORE STARTING:
1. Ensure you have database admin access
2. Verify pg_dump and pg_restore are installed
3. Schedule a maintenance window (estimated: 10-15 minutes)
4. Notify your team of the migration

STEP-BY-STEP PRODUCTION MIGRATION:

1. CREATE BACKUP (REQUIRED):
   python production_migration_plan.py backup <DATABASE_URL>

2. VALIDATE CURRENT STATE:
   python production_migration_plan.py validate <DATABASE_URL>

3. RUN MIGRATION:
   python production_migration_plan.py migrate <DATABASE_URL>

4. TEST API ENDPOINTS:
   python production_migration_plan.py test <DATABASE_URL>

5. VERIFY IN APP:
   - Generate a new training session
   - Check that drills show proper skill categories
   - Verify drill groups display correctly

EMERGENCY ROLLBACK (if needed):
   python production_migration_plan.py rollback <DATABASE_URL>

EXPECTED RESULTS:
- Drills will show proper skill categories (Passing, Shooting, etc.)
- Session generation will use proper skill balancing
- No downtime or data loss

WHAT GETS FIXED:
- ~118 drills missing skill focus entries
- Drill-to-skill relationships using UUIDs
- Proper skill categorization in API responses

MONITORING:
- Check application logs for any drill-related errors
- Monitor session generation performance
- Verify user experience improvements

If you encounter any issues, contact your development team immediately.
""")


def main():
    """Main migration function"""
    if len(sys.argv) < 2:
        print_production_migration_guide()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "guide":
        print_production_migration_guide()
        return
    
    if len(sys.argv) < 3:
        print("Error: DATABASE_URL required")
        print("Usage: python production_migration_plan.py <command> <DATABASE_URL>")
        sys.exit(1)
    
    database_url = sys.argv[2]
    migrator = ProductionMigrator(database_url)
    
    try:
        if command == "backup":
            success = migrator.create_full_backup()
            sys.exit(0 if success else 1)
            
        elif command == "validate":
            validation = migrator.validate_current_state()
            sys.exit(0 if validation else 1)
            
        elif command == "migrate":
            # Require backup first
            backup_exists = Path(migrator.backup_file.replace(
                datetime.now().strftime('%Y%m%d_%H%M%S'),
                '*'
            )).parent.glob(f"bravoball_backup_{migrator.db_name}_*.sql")
            
            if not any(backup_exists):
                logger.error("❌ No backup found! Create backup first:")
                logger.error(f"   python {sys.argv[0]} backup {database_url}")
                sys.exit(1)
            
            success = migrator.run_migration()
            sys.exit(0 if success else 1)
            
        elif command == "test":
            success = migrator.test_api_endpoints()
            sys.exit(0 if success else 1)
            
        elif command == "rollback":
            success = migrator.emergency_rollback()
            sys.exit(0 if success else 1)
            
        else:
            print(f"Unknown command: {command}")
            print("Available commands: backup, validate, migrate, test, rollback, guide")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Operation failed: {e}")
        sys.exit(1)
    finally:
        migrator.close()


if __name__ == "__main__":
    main() 