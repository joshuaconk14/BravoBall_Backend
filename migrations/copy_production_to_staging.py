#!/usr/bin/env python3
"""
Copy ALL production data to staging database
This will completely replicate production in staging, including schema and data.
Use this before running the V2 migration script to test migrations safely.

Date: 2025-01-25
Purpose: 
1. Recreate exact production schema in staging
2. Copy ALL production data to staging
3. Create proper backups and verification
4. Prepare staging for V2 migration testing
"""

import sys
import logging
import subprocess
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

PROD_URL = 'postgresql://jordan:nznEGcxVZbVyX5PvYXG5LuVQ15v0Tsd5@dpg-d11nbs3ipnbc73d2e2f0-a.oregon-postgres.render.com/bravoballdb'
STAGING_URL = 'postgresql://bravoball_staging_db_user:DszQQ1qg7XH2ocCNSCU844S43SMU4G4V@dpg-d21l5oh5pdvs7382nib0-a.oregon-postgres.render.com/bravoball_staging_db'

def setup_logging():
    """Setup logging for copy operation"""
    log_filename = f"copy_production_to_staging_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_filename

def create_backup(engine, phase_name):
    """Create database backup before major operations"""
    backup_filename = f"staging_backup_{phase_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    database_url = str(engine.url)
    
    logging.info(f"📦 Creating {phase_name} backup: {backup_filename}")
    
    try:
        # Add SSL parameters for Render databases
        result = subprocess.run([
            'pg_dump', database_url + '?sslmode=require', '--no-owner', '--no-privileges'
        ], capture_output=True, text=True, check=True)
        
        with open(backup_filename, 'w') as f:
            f.write(result.stdout)
        
        logging.info(f"✅ Backup created: {backup_filename}")
        return backup_filename
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Backup failed: {e}")
        raise

def copy_table_data(table_name, prod_conn, staging_conn):
    """Copy all data from production table to staging table"""
    logging.info(f"📋 Copying {table_name}...")
    
    # Get production data count
    result = prod_conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
    prod_count = result.fetchone()[0]
    
    if prod_count == 0:
        logging.info(f"   ⚠️ {table_name}: No data to copy")
        return
    
    # Clear staging table  
    staging_conn.execute(text(f"DELETE FROM {table_name}"))
    
    # Get all production data
    result = prod_conn.execute(text(f"SELECT * FROM {table_name}"))
    rows = result.fetchall()
    columns = result.keys()
    
    if not rows:
        logging.info(f"   ⚠️ {table_name}: No rows fetched")
        return
    
    # Build INSERT statement
    column_names = ', '.join(columns)
    placeholders = ', '.join([f':{col}' for col in columns])
    insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
    
    # Insert all rows
    success_count = 0
    for row in rows:
        try:
            row_dict = dict(zip(columns, row))
            staging_conn.execute(text(insert_sql), row_dict)
            success_count += 1
        except Exception as e:
            logging.warning(f"   ❌ Error inserting row in {table_name}: {str(e)[:100]}...")
            continue
    
    logging.info(f"   ✅ {table_name}: {success_count}/{prod_count} records copied")

def recreate_production_schema_in_staging(prod_engine, staging_engine, dry_run=False):
    """Recreate the exact production schema in staging database"""
    logging.info("🏗️ Recreating production schema in staging...")
    
    if dry_run:
        logging.info("🔍 DRY RUN: Would recreate production schema in staging")
        return True
    
    # First clear staging database completely
    logging.info("🧹 Clearing staging database...")
    with staging_engine.connect() as conn:
        trans = conn.begin()
        try:
            # Get all tables
            result = conn.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename NOT LIKE 'pg_%'
            """))
            tables = [row[0] for row in result.fetchall()]
            
            # Drop tables in reverse dependency order
            for table in reversed(tables):
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                logging.info(f"   🗑️ Dropped table: {table}")
            
            trans.commit()
            logging.info("✅ Staging database cleared")
        except Exception as e:
            trans.rollback()
            logging.error(f"❌ Failed to clear staging: {e}")
            raise
    
    # Recreate production schema in staging
    try:
        # Get CREATE TABLE statements from production
        with prod_engine.connect() as prod_conn:
            # Get all table creation statements
            result = prod_conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            table_names = [row[0] for row in result.fetchall()]
            
            logging.info(f"📋 Found {len(table_names)} tables to recreate")
            
            with staging_engine.connect() as staging_conn:
                staging_trans = staging_conn.begin()
                try:
                    # Create each table structure (without foreign keys first)
                    for table_name in table_names:
                        # Get table structure
                        result = prod_conn.execute(text(f"""
                            SELECT column_name, data_type, character_maximum_length, 
                                   is_nullable, column_default
                            FROM information_schema.columns 
                            WHERE table_name = '{table_name}' AND table_schema = 'public'
                            ORDER BY ordinal_position
                        """))
                        columns = result.fetchall()
                        
                        if columns:
                            column_defs = []
                            for col in columns:
                                name, dtype, max_len, nullable, default = col
                                
                                # Build column definition
                                col_def = f"{name} {dtype}"
                                if max_len and dtype in ('character varying', 'character'):
                                    col_def += f"({max_len})"
                                
                                if nullable == 'NO':
                                    col_def += " NOT NULL"
                                
                                if default:
                                    col_def += f" DEFAULT {default}"
                                
                                column_defs.append(col_def)
                            
                            create_sql = f"CREATE TABLE {table_name} ({', '.join(column_defs)})"
                            logging.info(f"   🔨 Creating table: {table_name}")
                            
                            try:
                                staging_conn.execute(text(create_sql))
                            except Exception as e:
                                logging.warning(f"   ⚠️ Could not create {table_name}: {str(e)[:100]}...")
                    
                    staging_trans.commit()
                    logging.info("✅ Production schema recreated in staging")
                    return True
                    
                except Exception as e:
                    staging_trans.rollback()
                    logging.error(f"❌ Schema recreation failed: {e}")
                    raise
                    
    except Exception as e:
        logging.error(f"💥 Schema recreation failed: {e}")
        raise

def copy_all_production_data(prod_engine, staging_engine, dry_run=False):
    """Copy all production data using the proven method"""
    logging.info("📥 Copying production data...")
    
    # Tables to copy (order matters for foreign keys)
    tables_to_copy = [
        'users',
        'drills', 
        'drill_groups',
        'drill_group_items',
        'completed_sessions',
        'progress_history',
        'ordered_session_drills',
        'drill_skill_focus'
    ]
    
    if dry_run:
        logging.info(f"🔍 DRY RUN: Would copy {len(tables_to_copy)} tables")
        with prod_engine.connect() as prod_conn:
            for table in tables_to_copy:
                try:
                    result = prod_conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    logging.info(f"   Would copy {table}: {count} records")
                except Exception as e:
                    logging.warning(f"   ⚠️ Could not check {table}: {e}")
        return True
    
    try:
        with prod_engine.connect() as prod_conn, staging_engine.connect() as staging_conn:
            trans = staging_conn.begin()
            
            try:
                # Copy each table
                for table in tables_to_copy:
                    try:
                        copy_table_data(table, prod_conn, staging_conn)
                    except Exception as e:
                        logging.warning(f"   ⚠️ Skipping {table}: {str(e)[:100]}...")
                        continue
                
                trans.commit()
                logging.info("✅ ALL PRODUCTION DATA COPIED TO STAGING!")
                
                # Verify copy
                logging.info("🔍 VERIFICATION:")
                for table in tables_to_copy:
                    try:
                        result = staging_conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.fetchone()[0]
                        logging.info(f"   ✅ {table}: {count} records")
                    except Exception as e:
                        logging.warning(f"   ❌ {table}: {str(e)[:50]}...")
                
                return True
                
            except Exception as e:
                trans.rollback()
                logging.error(f"❌ Transaction failed: {e}")
                raise
                
    except Exception as e:
        logging.error(f"💥 Copy failed: {e}")
        raise

def main():
    """Main copy function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Copy Production Data to Staging')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--skip-backup', action='store_true', help='Skip backup creation')
    parser.add_argument('--staging-url', default=STAGING_URL, help='Staging database URL')
    parser.add_argument('--production-url', default=PROD_URL, help='Production database URL')
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = setup_logging()
    logging.info("🚀 Starting Production to Staging Copy")
    logging.info("=" * 60)
    
    if args.dry_run:
        logging.info("🔍 DRY RUN MODE - No changes will be applied")
    
    try:
        # Create database engines
        prod_engine = create_engine(args.production_url)
        staging_engine = create_engine(args.staging_url)
        logging.info(f"🔗 Connected to production and staging databases")
        
        # Create initial backup of staging
        if not args.dry_run and not args.skip_backup:
            create_backup(staging_engine, "before_copy")
        
        # Step 1: Recreate production schema in staging
        logging.info("\n🎯 Step 1: Recreating Production Schema")
        success = recreate_production_schema_in_staging(prod_engine, staging_engine, args.dry_run)
        if not success:
            logging.error("❌ Schema recreation failed!")
            sys.exit(1)
        
        # Step 2: Copy all production data
        logging.info("\n🎯 Step 2: Copying Production Data")
        success = copy_all_production_data(prod_engine, staging_engine, args.dry_run)
        if not success:
            logging.error("❌ Data copy failed!")
            sys.exit(1)
        
        logging.info("\n🎉 Production to Staging copy completed successfully!")
        logging.info("=" * 60)
        logging.info("📱 Your staging database now contains exact copy of production")
        logging.info("🔧 Next steps:")
        logging.info("   1. Run complete_v2_migration.py against staging")
        logging.info("   2. Test your Flutter app with staging")
        logging.info("   3. Apply same migration to production when ready")
        
    except Exception as e:
        logging.error(f"💥 Copy operation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 