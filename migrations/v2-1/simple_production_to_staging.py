#!/usr/bin/env python3
"""
Production to Target Database Copy (Staging or V2)
Uses pg_dump and psql for reliable data copying with environment variable support

This script:
1. Creates a production data dump using pg_dump
2. Clears target database (staging or V2)
3. Restores production dump to target using psql

Environment Variables Required:
    PRODUCTION_DATABASE_URL, STAGING_DATABASE_URL, V2_DATABASE_URL

Usage:
    # Copy to staging (default)
    python migrations/v2-1/simple_production_to_staging.py
    
    # Copy to V2 database (blue-green deployment)
    python migrations/v2-1/simple_production_to_staging.py --target-db v2
    
    # Dry run test
    python migrations/v2-1/simple_production_to_staging.py --dry-run --target-db v2
"""

import os
import sys
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Database URLs - Now using environment variables
def get_database_urls():
    """Get database URLs from environment variables with fallbacks"""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Production database URL
    prod_url = os.getenv('PRODUCTION_DATABASE_URL')
    if not prod_url:
        # Fallback to legacy hard-coded URL for backwards compatibility
        prod_url = 'postgresql://jordan:nznEGcxVZbVyX5PvYXG5LuVQ15v0Tsd5@dpg-d11nbs3ipnbc73d2e2f0-a.oregon-postgres.render.com/bravoballdb'
        logging.warning("⚠️ Using fallback PRODUCTION_DATABASE_URL. Set PRODUCTION_DATABASE_URL environment variable.")
    
    # Staging database URL  
    staging_url = os.getenv('STAGING_DATABASE_URL')
    if not staging_url:
        # Fallback to legacy hard-coded URL for backwards compatibility
        staging_url = 'postgresql://bravoball_staging_db_user:DszQQ1qg7XH2ocCNSCU844S43SMU4G4V@dpg-d21l5oh5pdvs7382nib0-a.oregon-postgres.render.com/bravoball_staging_db'
        logging.warning("⚠️ Using fallback STAGING_DATABASE_URL. Set STAGING_DATABASE_URL environment variable.")
    
    # V2 database URL (for blue-green deployment)
    v2_url = os.getenv('V2_DATABASE_URL')
    if not v2_url:
        v2_url = staging_url  # Default to staging for now
        logging.info("ℹ️ V2_DATABASE_URL not set, using staging URL as default")
    
    return prod_url, staging_url, v2_url

# Initialize database URLs
PROD_URL, STAGING_URL, V2_URL = get_database_urls()

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

def clear_target_database(target_url, target_name, dry_run=False):
    """Clear target database"""
    logging.info(f"🧹 Clearing {target_name}")
    
    if dry_run:
        logging.info(f"🔍 DRY RUN: Would clear {target_name}")
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
        cmd = ['psql', target_url, '-f', temp_script]
        success = run_command(cmd, f"Clearing {target_name}")
        
        # Clean up temp file
        if os.path.exists(temp_script):
            os.remove(temp_script)
        
        return success
        
    except Exception as e:
        logging.error(f"❌ Failed to clear staging: {e}")
        return False

def restore_to_target(dump_file, target_url, target_name, dry_run=False):
    """Restore production dump to target database"""
    logging.info(f"📥 Restoring {dump_file} to {target_name}")
    
    if dry_run:
        logging.info(f"🔍 DRY RUN: Would restore production dump to {target_name}")
        return True
    
    if not os.path.exists(dump_file):
        logging.error(f"❌ Dump file not found: {dump_file}")
        return False
    
    cmd = ['psql', target_url, '-f', dump_file]
    success = run_command(cmd, f"Restoring {dump_file} to {target_name}")
    
    return success

def verify_target_data(target_url, target_name, dry_run=False):
    """Verify target database has data"""
    logging.info(f"🔍 Verifying {target_name} data")
    
    if dry_run:
        logging.info(f"🔍 DRY RUN: Would verify {target_name} data")
        return True
    
    # Check key tables
    tables_to_check = ['users', 'drills', 'drill_groups', 'completed_sessions']
    
    try:
        for table in tables_to_check:
            cmd = ['psql', target_url, '-c', f'SELECT COUNT(*) FROM {table};']
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
    
    parser = argparse.ArgumentParser(description='Simple Production to Target Database Copy')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--production-url', default=PROD_URL, help='Production database URL (source)')
    parser.add_argument('--staging-url', default=STAGING_URL, help='Staging database URL')
    parser.add_argument('--v2-url', default=V2_URL, help='V2 database URL (for blue-green deployment)')
    parser.add_argument('--target-db', choices=['staging', 'v2'], default='staging', 
                        help='Target database for copy (staging or v2)')
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = setup_logging()
    
    # Determine target database URL based on --target-db argument
    if args.target_db == 'v2':
        target_url = args.v2_url
        target_name = "V2 database"
    else:
        target_url = args.staging_url
        target_name = "staging database"
    
    logging.info(f"🚀 Starting Production to {target_name.title()} Copy")
    logging.info("=" * 60)
    logging.info(f"📍 Source: Production database")
    logging.info(f"📍 Target: {target_name}")
    logging.info(f"📍 Target URL: {target_url[:50]}...")  # Show partial URL
    
    if args.dry_run:
        logging.info("🔍 DRY RUN MODE - No changes will be applied")
    
    try:
        # Step 1: Create production dump
        logging.info("\n🎯 Step 1: Creating Production Dump")
        dump_file = create_production_dump(args.dry_run)
        if not dump_file:
            logging.error("❌ Failed to create production dump")
            sys.exit(1)
        
        # Step 2: Clear target database
        logging.info(f"\n🎯 Step 2: Clearing {target_name.title()}")
        if not clear_target_database(target_url, target_name, args.dry_run):
            logging.error(f"❌ Failed to clear {target_name}")
            sys.exit(1)
        
        # Step 3: Restore to target database
        logging.info(f"\n🎯 Step 3: Restoring to {target_name.title()}")
        if not restore_to_target(dump_file, target_url, target_name, args.dry_run):
            logging.error(f"❌ Failed to restore to {target_name}")
            sys.exit(1)
        
        # Step 4: Verify
        logging.info("\n🎯 Step 4: Verification")
        if not verify_target_data(target_url, target_name, args.dry_run):
            logging.error("❌ Verification failed")
            sys.exit(1)
        
        logging.info(f"\n🎉 Production to {target_name.title()} copy completed successfully!")
        logging.info("=" * 60)
        logging.info(f"📱 Your {target_name} now contains exact copy of production")
        logging.info("🔧 Next steps:")
        if args.target_db == 'v2':
            logging.info("   1. Run complete_v2_migration.py --target-db v2 --skip-data-import")
            logging.info("   2. Test your Flutter app with V2 backend")
            logging.info("   3. Update Flutter app to use V2 for production")
        else:
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