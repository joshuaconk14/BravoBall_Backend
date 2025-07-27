#!/usr/bin/env python3
"""
Simple Production to Staging Copy
Uses pg_dump and psql for reliable data copying

This script:
1. Creates a production data dump using pg_dump
2. Clears staging database
3. Restores production dump to staging using psql

Usage:
    python migrations/working-scripts/simple_production_to_staging.py
    python migrations/working-scripts/simple_production_to_staging.py --dry-run
"""

import os
import sys
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Database URLs
PROD_URL = 'postgresql://jordan:nznEGcxVZbVyX5PvYXG5LuVQ15v0Tsd5@dpg-d11nbs3ipnbc73d2e2f0-a.oregon-postgres.render.com/bravoballdb'
STAGING_URL = 'postgresql://bravoball_staging_db_user:DszQQ1qg7XH2ocCNSCU844S43SMU4G4V@dpg-d21l5oh5pdvs7382nib0-a.oregon-postgres.render.com/bravoball_staging_db'

def setup_logging():
    """Setup logging in v2-1 directory"""
    # Create logs directory within v2-1
    script_dir = Path(__file__).parent
    logs_dir = script_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    log_filename = logs_dir / f"production_to_staging_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(str(log_filename)),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return str(log_filename)

def run_command(cmd, description, dry_run=False):
    """Run a shell command with logging"""
    logging.info(f"🔄 {description}")
    
    if dry_run:
        logging.info(f"🔍 DRY RUN: Would run: {' '.join(cmd[:3])}...")
        return True
    
    try:
        logging.info(f"   Running: {' '.join(cmd[:3])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logging.info(f"   ✅ Success: {description}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"   ❌ Failed: {description}")
        logging.error(f"   Error: {e.stderr[:200]}...")
        return False
    except Exception as e:
        logging.error(f"   ❌ Error: {str(e)}")
        return False

def create_production_dump(dry_run=False):
    """Create production database dump in v2-1/backups directory"""
    # Create backups directory within v2-1
    script_dir = Path(__file__).parent
    backups_dir = script_dir / "backups"
    backups_dir.mkdir(exist_ok=True)
    
    dump_filename = backups_dir / f"production_data_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    logging.info(f"📦 Creating production dump: {dump_filename}")
    
    if dry_run:
        logging.info("🔍 DRY RUN: Would create production dump")
        return str(backups_dir / "production_data_dump.sql")
    
    cmd = [
        'pg_dump',
        PROD_URL,
        '--no-owner',
        '--no-privileges', 
        '--clean',
        '--if-exists',
        '--file', str(dump_filename)
    ]
    
    success = run_command(cmd, f"Creating production dump", dry_run=False)
    if success:
        logging.info(f"   ✅ Dump created: {dump_filename}")
        return str(dump_filename)
    else:
        logging.error(f"   ❌ Failed to create dump")
        return None

def clear_staging_database(dry_run=False):
    """Clear staging database"""
    logging.info("🧹 Clearing staging database")
    
    if dry_run:
        logging.info("🔍 DRY RUN: Would clear staging database")
        return True
    
    # Create a temporary SQL script to drop all tables
    drop_script = """
-- Drop all tables and sequences
DO $$ DECLARE
    r RECORD;
BEGIN
    -- Drop all tables
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') 
    LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
    
    -- Drop all sequences
    FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public')
    LOOP
        EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(r.sequence_name) || ' CASCADE';
    END LOOP;
END $$;
"""
    
    try:
        # Write script to temp file
        temp_script = "temp_clear_staging.sql"
        with open(temp_script, 'w') as f:
            f.write(drop_script)
        
        # Run the script
        cmd = ['psql', STAGING_URL, '-f', temp_script]
        success = run_command(cmd, "Clearing staging database")
        
        # Clean up temp file
        if os.path.exists(temp_script):
            os.remove(temp_script)
        
        return success
        
    except Exception as e:
        logging.error(f"❌ Failed to clear staging: {e}")
        return False

def restore_to_staging(dump_file, dry_run=False):
    """Restore production dump to staging"""
    logging.info(f"📥 Restoring {dump_file} to staging")
    
    if dry_run:
        logging.info("🔍 DRY RUN: Would restore production dump to staging")
        return True
    
    if not os.path.exists(dump_file):
        logging.error(f"❌ Dump file not found: {dump_file}")
        return False
    
    cmd = ['psql', STAGING_URL, '-f', dump_file]
    success = run_command(cmd, f"Restoring {dump_file} to staging")
    
    return success

def verify_staging_data(dry_run=False):
    """Verify staging has data"""
    logging.info("🔍 Verifying staging data")
    
    if dry_run:
        logging.info("🔍 DRY RUN: Would verify staging data")
        return True
    
    # Check key tables
    tables_to_check = ['users', 'drills', 'drill_groups', 'completed_sessions']
    
    try:
        for table in tables_to_check:
            cmd = ['psql', STAGING_URL, '-c', f'SELECT COUNT(*) FROM {table};']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Extract count from result (crude but effective)
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip().isdigit():
                    count = int(line.strip())
                    logging.info(f"   ✅ {table}: {count} records")
                    break
        
        logging.info("✅ Staging verification completed")
        return True
        
    except Exception as e:
        logging.error(f"❌ Verification failed: {e}")
        return False

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple Production to Staging Copy')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = setup_logging()
    
    logging.info("🚀 Starting Simple Production to Staging Copy")
    logging.info("=" * 60)
    
    if args.dry_run:
        logging.info("🔍 DRY RUN MODE - No changes will be applied")
    
    try:
        # Step 1: Create production dump
        logging.info("\n🎯 Step 1: Creating Production Dump")
        dump_file = create_production_dump(args.dry_run)
        if not dump_file:
            logging.error("❌ Failed to create production dump")
            sys.exit(1)
        
        # Step 2: Clear staging
        logging.info("\n🎯 Step 2: Clearing Staging Database")
        if not clear_staging_database(args.dry_run):
            logging.error("❌ Failed to clear staging database")
            sys.exit(1)
        
        # Step 3: Restore to staging
        logging.info("\n🎯 Step 3: Restoring to Staging")
        if not restore_to_staging(dump_file, args.dry_run):
            logging.error("❌ Failed to restore to staging")
            sys.exit(1)
        
        # Step 4: Verify
        logging.info("\n🎯 Step 4: Verification")
        if not verify_staging_data(args.dry_run):
            logging.error("❌ Verification failed")
            sys.exit(1)
        
        logging.info("\n🎉 Production to Staging copy completed successfully!")
        logging.info("=" * 60)
        logging.info("📱 Your staging database now contains exact copy of production")
        logging.info("🔧 Next steps:")
        logging.info("   1. Run complete_v2_migration.py --skip-data-import")
        logging.info("   2. Test your Flutter app with staging")
        logging.info("   3. Apply same migration to production when ready")
        
        # Clean up dump file if requested
        if not args.dry_run and dump_file and os.path.exists(dump_file):
            try:
                os.remove(dump_file)
                logging.info(f"🧹 Cleaned up dump file: {dump_file}")
            except:
                logging.warning(f"⚠️ Could not clean up: {dump_file}")
        
    except KeyboardInterrupt:
        logging.info("\n⚠️ Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"💥 Operation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()