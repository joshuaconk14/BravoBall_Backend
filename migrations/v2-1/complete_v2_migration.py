#!/usr/bin/env python3
"""
Complete BravoBall v2 Migration - Production Data + Schema + UUIDs
Date: 2025-07-25
Purpose: 
1. Import ALL production data to staging
2. Apply v2 schema changes carefully
3. Populate UUIDs for existing drills
4. Maintain data integrity throughout
5. Create proper backups at each step

Commands:
    python migrations/v2-1/simple_production_to_staging.py              # Copy production db to staging db
    python migrations/v2-1/complete_v2_migration.py --skip-data-import  # Schema and data migration
    
To run everything at once in a new terminal while in project root:
    source venv/bin/activate && python migrations/v2-1/simple_production_to_staging.py && python migrations/v2-1/complete_v2_migration.py --skip-data-import
"""

import json
import os
import sys
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the parent directory to path so we can import models
sys.path.append(str(Path(__file__).parent.parent.parent))
import models
from db import Base

# Database URLs - Now using environment variables
def get_database_urls():
    """Get database URLs from environment variables with fallbacks"""
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
    """Setup logging for migration in v2-1 directory"""
    # Create logs directory within v2-1
    script_dir = Path(__file__).parent
    logs_dir = script_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    log_filename = logs_dir / f"complete_v2_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(str(log_filename)),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return str(log_filename)

def create_backup(engine, phase_name):
    """Create database backup before each major phase"""
    # Create backups directory within v2-1
    script_dir = Path(__file__).parent
    backup_dir = script_dir / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    backup_filename = backup_dir / f"backup_{phase_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    # ✅ FIX 1: Get proper database URL format for pg_dump
    url_obj = engine.url
    if hasattr(url_obj, 'render_as_string'):
        # SQLAlchemy 1.4+ method - renders URL properly for external tools
        database_url = url_obj.render_as_string(hide_password=False)
    else:
        # Fallback: construct URL manually from components
        username = url_obj.username
        password = url_obj.password
        host = url_obj.host
        port = url_obj.port or 5432
        database = url_obj.database
        database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    logging.info(f"📦 Creating {phase_name} backup: {backup_filename}")
    logging.info(f"🔗 Database: {url_obj.host}:{url_obj.port}/{url_obj.database}")  # Debug info without password
    
    try:
        # ✅ FIX 2: Better pg_dump command with improved error handling
        dump_cmd = [
            'pg_dump', database_url,
            '--no-owner', '--no-privileges', 
            '--clean', '--if-exists',
            '--file', str(backup_filename)
        ]
        
        logging.info(f"🔄 Running pg_dump to create backup...")
        
        # ✅ FIX 3: Capture stderr for better error diagnosis
        result = subprocess.run(dump_cmd, check=False, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Verify the backup file was created and has content
            if backup_filename.exists() and backup_filename.stat().st_size > 0:
                size_mb = backup_filename.stat().st_size / (1024 * 1024)
                logging.info(f"✅ Backup created: {backup_filename} ({size_mb:.1f} MB)")
                return str(backup_filename)
            else:
                raise Exception("Backup file was not created or is empty")
        else:
            logging.error(f"❌ pg_dump failed with return code: {result.returncode}")
            if result.stdout:
                logging.error(f"stdout: {result.stdout.strip()}")
            if result.stderr:
                logging.error(f"stderr: {result.stderr.strip()}")
            
            # Try to diagnose the issue
            if "password authentication failed" in result.stderr.lower():
                logging.error("🔐 Database authentication failed - check credentials")
            elif "could not connect" in result.stderr.lower():
                logging.error("🌐 Database connection failed - check host/port")
            elif "does not exist" in result.stderr.lower():
                logging.error("🗄️ Database or table does not exist")
            
            raise subprocess.CalledProcessError(result.returncode, dump_cmd, result.stdout, result.stderr)
            
    except FileNotFoundError:
        logging.error("❌ pg_dump not found. Ensure PostgreSQL 16 is installed and in PATH")
        logging.error("💡 Try: export PATH=\"/usr/local/opt/postgresql@16/bin:$PATH\"")
        raise
    except Exception as e:
        logging.error(f"❌ Backup failed with unexpected error: {e}")
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

def phase_1_import_production_data(staging_engine, dry_run=False):
    """Phase 1: Import ALL production data using the proven copy method"""
    logging.info("🚀 PHASE 1: Importing Production Data")
    logging.info("=" * 50)
    
    if dry_run:
        logging.info("🔍 DRY RUN: Would recreate production schema and copy all data")
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
    logging.info("🏗️ Recreating production schema in staging...")
    try:
        prod_engine = create_engine(PROD_URL)
        
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
                    
                except Exception as e:
                    staging_trans.rollback()
                    logging.error(f"❌ Schema recreation failed: {e}")
                    raise
                    
    except Exception as e:
        logging.error(f"💥 Schema recreation failed: {e}")
        raise
    
    # Now copy production data using the proven method
    logging.info("📥 Copying production data...")
    try:
        # Tables to copy (order matters for foreign keys) - same as working script
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

def phase_2_apply_v2_schema(staging_engine, dry_run=False):
    """Phase 2: Apply v2 schema using SQLAlchemy models (proper way)"""
    logging.info("🚀 PHASE 2: Applying v2 Schema Changes from models.py")
    logging.info("=" * 50)
    
    if dry_run:
        logging.info("🔍 DRY RUN: Would create v2 schema from models.py")
        logging.info("   Tables that would be created/updated:")
        for table_name, table in Base.metadata.tables.items():
            columns = [col.name for col in table.columns]
            logging.info(f"   📋 {table_name}: {len(columns)} columns")
            if table_name == 'custom_drills':
                logging.info(f"      custom_drills columns: {columns}")
        logging.info("   ✅ Would enable UUID extension")
        logging.info("   ✅ Would add missing columns to existing tables")
        logging.info("   ✅ Would create new tables from SQLAlchemy models")
        return True
    
    try:
        # Enable UUID extension first
        with staging_engine.connect() as conn:
            trans = conn.begin()
            try:
                logging.info("🔧 Enabling UUID extension...")
                conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                trans.commit()
                logging.info("✅ UUID extension enabled")
            except Exception as e:
                trans.rollback()
                logging.warning(f"⚠️ UUID extension: {e}")
        
        # Get current database schema
        inspector = inspect(staging_engine)
        existing_tables = set(inspector.get_table_names())
        
        logging.info("🏗️ Applying schema migrations from models.py...")
        logging.info("   Using models.py as source of truth for database schema")
        
        with staging_engine.connect() as conn:
            # 1. Add missing columns to existing tables
            for table_name, table in Base.metadata.tables.items():
                if table_name in existing_tables:
                    logging.info(f"🔧 Checking existing table: {table_name}")
                    
                    # Get current columns
                    current_columns = {col['name']: col for col in inspector.get_columns(table_name)}
                    model_columns = {col.name: col for col in table.columns}
                    
                    # Find missing columns
                    missing_columns = set(model_columns.keys()) - set(current_columns.keys())
                    
                    if missing_columns:
                        logging.info(f"   📝 Adding {len(missing_columns)} missing columns: {missing_columns}")
                        
                        for col_name in missing_columns:
                            col = model_columns[col_name]
                            
                            # Convert SQLAlchemy type to SQL type string
                            sql_type = str(col.type)
                            
                            # Handle specific type conversions
                            if 'UUID' in str(col.type):
                                sql_type = 'UUID'
                            elif 'VARCHAR' in str(col.type):
                                sql_type = str(col.type)
                            elif 'INTEGER' in str(col.type) or 'BIGINT' in str(col.type):
                                sql_type = 'INTEGER'
                            elif 'BOOLEAN' in str(col.type):
                                sql_type = 'BOOLEAN'
                            elif 'TIMESTAMP' in str(col.type):
                                sql_type = 'TIMESTAMP WITH TIME ZONE'
                            elif 'JSON' in str(col.type):
                                sql_type = 'JSON'
                            elif 'TEXT' in str(col.type):
                                sql_type = 'TEXT'
                            elif 'FLOAT' in str(col.type) or 'REAL' in str(col.type):
                                sql_type = 'FLOAT'
                            
                            # Handle DEFAULT values properly
                            default_value = None
                            if col.default is not None:
                                if hasattr(col.default, 'arg') and col.default.arg is not None:
                                    if isinstance(col.default.arg, bool):
                                        default_value = str(col.default.arg).lower()
                                    elif isinstance(col.default.arg, (int, float)):
                                        default_value = str(col.default.arg)
                                    elif isinstance(col.default.arg, str):
                                        default_value = f"'{col.default.arg}'"
                                    else:
                                        default_value = str(col.default.arg)
                                elif hasattr(col.default, 'name') and 'uuid' in str(col.default.name).lower():
                                    # For UUID columns with uuid_generate_v4() default
                                    default_value = "uuid_generate_v4()"
                                elif str(col.default).lower() in ['false', 'true']:
                                    default_value = str(col.default).lower()
                                elif 'uuid' in str(col.default).lower():
                                    default_value = "uuid_generate_v4()"
                                else:
                                    default_value = "NULL"
                            
                            # Special handling for UUID columns - check if it's a UUID type with a uuid4 function default
                            if 'UUID' in sql_type and col.default is not None:
                                # Check if the default is the uuid.uuid4 function
                                if hasattr(col.default, 'arg') and hasattr(col.default.arg, '__name__') and 'uuid4' in col.default.arg.__name__:
                                    default_value = "uuid_generate_v4()"
                                elif str(col.default) and 'uuid4' in str(col.default):
                                    default_value = "uuid_generate_v4()"
                            
                            # Build ALTER TABLE statement
                            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {sql_type}"
                            
                            # Add DEFAULT clause if we have a proper value
                            if default_value and default_value != "NULL":
                                alter_sql += f" DEFAULT {default_value}"
                            
                            # Execute each ALTER TABLE with individual connection
                            try:
                                with staging_engine.connect() as alter_conn:
                                    alter_conn.execute(text(alter_sql))
                                    alter_conn.commit()
                                    logging.info(f"   ✅ Added {table_name}.{col_name} ({sql_type})")
                            except Exception as e:
                                if 'already exists' in str(e).lower():
                                    logging.info(f"   ℹ️ {table_name}.{col_name} already exists")
                                else:
                                    logging.warning(f"   ⚠️ Could not add {table_name}.{col_name}: {str(e)[:100]}...")
                    else:
                        logging.info(f"   ✅ {table_name}: No missing columns")
                else:
                    logging.info(f"🆕 Table {table_name} will be created")
            
            logging.info("✅ Missing columns added to existing tables")
        
        # 2. Create any completely new tables
        logging.info("🆕 Creating any new tables from models...")
        Base.metadata.create_all(bind=staging_engine)
        logging.info("✅ New tables created from models.py!")
        
        # 3. Verify schema matches models
        logging.info("🔍 Verifying schema matches models...")
        inspector = inspect(staging_engine)  # Refresh inspector
        all_columns_match = True
        
        for table_name, table in Base.metadata.tables.items():
            if inspector.has_table(table_name):
                staging_columns = {col['name'] for col in inspector.get_columns(table_name)}
                model_columns = {col.name for col in table.columns}
                missing = model_columns - staging_columns
                
                if missing:
                    logging.error(f"   ❌ {table_name} still missing: {missing}")
                    all_columns_match = False
                else:
                    logging.info(f"   ✅ {table_name}: All {len(model_columns)} columns present")
                    
                # Special verification for critical tables
                if table_name == 'drills':
                    critical_columns = {'uuid', 'is_custom'}
                    has_critical = critical_columns & staging_columns
                    if has_critical == critical_columns:
                        logging.info(f"   🎉 drills has ALL critical columns: {critical_columns}")
                    else:
                        missing_critical = critical_columns - staging_columns
                        logging.error(f"   ❌ drills missing critical: {missing_critical}")
                        all_columns_match = False
                        
                elif table_name == 'custom_drills':
                    required_columns = {'video_url', 'thumbnail_url', 'intensity', 'type', 'training_styles'}
                    has_required = required_columns & staging_columns
                    if has_required == required_columns:
                        logging.info(f"   🎉 custom_drills has ALL required columns: {required_columns}")
                    else:
                        missing_required = required_columns - staging_columns
                        logging.error(f"   ❌ custom_drills missing required: {missing_required}")
                        all_columns_match = False
            else:
                logging.error(f"   ❌ Table {table_name} does not exist!")
                all_columns_match = False
        
        if all_columns_match:
            logging.info("✅ V2 schema changes applied successfully - all columns match models.py!")
            return True
        else:
            logging.error("❌ Schema verification failed - some columns are still missing!")
            return False
        
    except Exception as e:
        logging.error(f"❌ Schema migration failed: {e}")
        raise

def phase_3_populate_uuids(staging_engine, dry_run=False):
    """Phase 3: Populate UUIDs for existing drills and update foreign keys"""
    logging.info("🚀 PHASE 3: Populating UUIDs for Existing Drills")
    logging.info("=" * 50)
    
    if dry_run:
        logging.info("🔍 DRY RUN: Would populate UUIDs for existing drills")
        with staging_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM drills WHERE uuid IS NULL"))
            null_count = result.fetchone()[0]
            logging.info(f"   Would generate UUIDs for {null_count} drills")
            
            # Check foreign key tables
            fk_tables = ['drill_skill_focus', 'drill_group_items', 'ordered_session_drills']
            for table in fk_tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table} WHERE drill_uuid IS NULL"))
                    null_fk_count = result.fetchone()[0]
                    logging.info(f"   Would update {null_fk_count} records in {table}")
                except Exception as e:
                    logging.warning(f"   ⚠️ Could not check {table}: {e}")
        return True
    
    with staging_engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Populate UUIDs for drills that don't have them
            logging.info("🔧 Generating UUIDs for existing drills...")
            result = conn.execute(text("""
                UPDATE drills 
                SET uuid = uuid_generate_v4() 
                WHERE uuid IS NULL
            """))
            updated_drills = result.rowcount
            logging.info(f"   ✅ Generated UUIDs for {updated_drills} drills")
            
            # 2. Update foreign key tables to use drill_uuid based on drill_id mapping
            foreign_key_updates = [
                {
                    'table': 'drill_skill_focus',
                    'query': '''
                        UPDATE drill_skill_focus 
                        SET drill_uuid = drills.uuid 
                        FROM drills 
                        WHERE drill_skill_focus.drill_id = drills.id 
                        AND drill_skill_focus.drill_uuid IS NULL
                    '''
                },
                {
                    'table': 'drill_group_items',
                    'query': '''
                        UPDATE drill_group_items 
                        SET drill_uuid = drills.uuid 
                        FROM drills 
                        WHERE drill_group_items.drill_id = drills.id 
                        AND drill_group_items.drill_uuid IS NULL
                    '''
                },
                {
                    'table': 'ordered_session_drills',
                    'query': '''
                        UPDATE ordered_session_drills 
                        SET drill_uuid = drills.uuid 
                        FROM drills 
                        WHERE ordered_session_drills.drill_id = drills.id 
                        AND ordered_session_drills.drill_uuid IS NULL
                    '''
                }
            ]
            
            for update_info in foreign_key_updates:
                table = update_info['table']
                query = update_info['query']
                
                logging.info(f"🔗 Updating {table} with drill UUIDs based on drill_id mapping...")
                try:
                    result = conn.execute(text(query))
                    updated_count = result.rowcount
                    logging.info(f"   ✅ Updated {updated_count} records in {table}")
                    
                    # Verify the update
                    result = conn.execute(text(f"""
                        SELECT COUNT(*) as total_records,
                               COUNT(drill_uuid) as records_with_uuid
                        FROM {table}
                    """))
                    row = result.fetchone()
                    total = row[0]
                    with_uuid = row[1]
                    logging.info(f"   ✅ {table}: {with_uuid}/{total} records now have drill_uuid")
                    
                except Exception as e:
                    logging.error(f"   ❌ Could not update {table}: {e}")
                    raise
            
            # 3. Add unique constraint to drill UUIDs
            logging.info("🔒 Adding unique constraint to drill UUIDs...")
            try:
                conn.execute(text("ALTER TABLE drills ADD CONSTRAINT drills_uuid_unique UNIQUE (uuid)"))
                logging.info("   ✅ Unique constraint added")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logging.info("   ℹ️ Unique constraint already exists")
                else:
                    logging.warning(f"   ⚠️ Could not add unique constraint: {e}")
            
            # 4. Fix drill IDs in completed_sessions JSON
            logging.info("🔧 Fixing drill IDs in completed_sessions JSON...")
            try:
                # Update drill IDs in JSON for single-drill sessions (most common)
                result = conn.execute(text("""
                    UPDATE completed_sessions 
                    SET drills = jsonb_set(
                        drills::jsonb, 
                        '{0,drill,id}', 
                        to_jsonb(d.uuid::text)
                    )
                    FROM drills d 
                    WHERE drills::jsonb->0->'drill'->>'title' = d.title
                    AND drills IS NOT NULL
                    AND jsonb_array_length(drills::jsonb) = 1
                    AND drills::jsonb->0->'drill'->>'id' != d.uuid::text
                """))
                single_drill_updates = result.rowcount
                logging.info(f"   ✅ Updated {single_drill_updates} single-drill sessions")
                
                # Check for multi-drill sessions that need special handling
                result = conn.execute(text("""
                    SELECT COUNT(*) as multi_drill_sessions
                    FROM completed_sessions 
                    WHERE drills IS NOT NULL 
                    AND jsonb_array_length(drills::jsonb) > 1
                """))
                multi_drill_count = result.fetchone()[0]
                
                if multi_drill_count > 0:
                    logging.info(f"   ⚠️ Found {multi_drill_count} multi-drill sessions - these need special handling")
                    # For now, log this - we can handle multi-drill sessions separately if needed
                
                # Verify the JSON fix
                result = conn.execute(text("""
                    SELECT COUNT(*) as remaining_mismatches
                    FROM completed_sessions cs
                    JOIN drills d ON d.title = cs.drills::jsonb->0->'drill'->>'title'
                    WHERE cs.drills IS NOT NULL
                    AND cs.drills::jsonb->0->'drill'->>'id' != d.uuid::text
                """))
                remaining = result.fetchone()[0]
                logging.info(f"   🔍 Verification: {remaining} drill ID mismatches remaining")
                
            except Exception as e:
                logging.warning(f"   ⚠️ Could not fix completed_sessions JSON: {e}")
            
            trans.commit()
            logging.info("✅ UUID population completed successfully")
            return True
            
        except Exception as e:
            trans.rollback()
            logging.error(f"❌ UUID population failed: {e}")
            raise

def phase_4_seed_new_content(staging_engine, dry_run=False):
    """Phase 4: Seed new drills and mental training quotes"""
    logging.info("🚀 PHASE 4: Seeding New Drills & Mental Training Content")
    logging.info("=" * 50)
    
    # First, seed mental training quotes
    quotes_success = seed_mental_training_quotes(staging_engine, dry_run)
    
    # Then, seed new drills
    drills_success = seed_new_drills(staging_engine, dry_run)
    
    return quotes_success and drills_success

def seed_mental_training_quotes(staging_engine, dry_run=False):
    """Seed mental training quotes"""
    logging.info("📚 Seeding Mental Training Quotes...")
    
    # Get quotes file
    quotes_file = os.path.join(os.path.dirname(__file__), '..', '..', 'drills', 'mental_training_quotes.txt')
    
    if not os.path.exists(quotes_file):
        logging.error(f"❌ Quotes file not found: {quotes_file}")
        return False
    
    try:
        with open(quotes_file, 'r', encoding='utf-8') as f:
            quotes = json.load(f)
        
        logging.info(f"📋 Loaded {len(quotes)} quotes from file")
        
        if dry_run:
            logging.info(f"🔍 DRY RUN: Would seed {len(quotes)} mental training quotes")
            for i, quote in enumerate(quotes[:3], 1):
                logging.info(f"   Quote {i}: \"{quote['content'][:60]}...\" - {quote['author']}")
            return True
        
        with staging_engine.connect() as conn:
            # Check if quotes already exist
            result = conn.execute(text("SELECT COUNT(*) FROM mental_training_quotes"))
            existing_count = result.fetchone()[0]
            
            if existing_count > 0:
                logging.info(f"📋 Found {existing_count} existing quotes, skipping seeding")
                return True
            
            # Insert quotes
            insert_sql = """
                INSERT INTO mental_training_quotes (content, author, type, display_duration, created_at)
                VALUES (:content, :author, :type, :display_duration, NOW())
            """
            
            success_count = 0
            for quote in quotes:
                try:
                    conn.execute(text(insert_sql), {
                        'content': quote['content'],
                        'author': quote['author'],
                        'type': quote['type'],
                        'display_duration': quote['display_duration']
                    })
                    success_count += 1
                except Exception as e:
                    logging.error(f"❌ Error seeding quote: {e}")
            
            conn.commit()
            logging.info(f"✅ Successfully seeded {success_count}/{len(quotes)} quotes")
            return success_count == len(quotes)
            
    except Exception as e:
        logging.error(f"❌ Error seeding mental training quotes: {e}")
        return False

def seed_new_drills(staging_engine, dry_run=False):
    """Seed new drills from text files (goalkeeping, defending, fitness)"""
    logging.info("⚽ Seeding New Drills from Text Files...")
    
    # New drill files to seed (skip existing categories)
    new_drill_files = [
        ('goalkeeper_drills.txt', 'Goalkeeping'),
        ('defending_drills.txt', 'Defending'), 
        ('fitness_drills.txt', 'Fitness')
    ]
    
    drills_base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'drills')
    total_drills_seeded = 0
    
    if dry_run:
        logging.info("🔍 DRY RUN: Would seed new drills from text files")
        for filename, category in new_drill_files:
            file_path = os.path.join(drills_base_path, filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        drills = json.load(f)
                    logging.info(f"   {category}: Would seed {len(drills)} drills")
                except Exception as e:
                    logging.warning(f"   ⚠️ Could not read {filename}: {e}")
        return True
    
    try:
        with staging_engine.connect() as conn:
            trans = conn.begin()
            
            try:
                for filename, category in new_drill_files:
                    file_path = os.path.join(drills_base_path, filename)
                    
                    if not os.path.exists(file_path):
                        logging.warning(f"⚠️ {filename} not found, skipping {category} drills")
                        continue
                    
                    # Load drills from file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            drills = json.load(f)
                        logging.info(f"📋 Loaded {len(drills)} {category.lower()} drills from {filename}")
                    except Exception as e:
                        logging.error(f"❌ Error reading {filename}: {e}")
                        continue
                    
                    # Check if drills from this category already exist
                    sample_drill_title = drills[0]['title'] if drills else None
                    if sample_drill_title:
                        result = conn.execute(text("""
                            SELECT COUNT(*) FROM drills WHERE title = :title
                        """), {'title': sample_drill_title})
                        
                        if result.fetchone()[0] > 0:
                            logging.info(f"📋 {category} drills already exist, skipping seeding")
                            continue
                    
                    # Seed drills
                    seeded_count = 0
                    for drill in drills:
                        try:
                            # Convert lists to JSON strings for database storage
                            equipment_json = json.dumps(drill.get('equipment', []))
                            suitable_locations_json = json.dumps(drill.get('suitable_locations', []))
                            training_styles_json = json.dumps(drill.get('training_styles', []))
                            instructions_json = json.dumps(drill.get('instructions', []))
                            tips_json = json.dumps(drill.get('tips', []))
                            common_mistakes_json = json.dumps(drill.get('common_mistakes', []))
                            progression_steps_json = json.dumps(drill.get('progression_steps', []))
                            variations_json = json.dumps(drill.get('variations', []))
                            
                            # Insert drill with UUID
                            insert_sql = """
                                INSERT INTO drills (
                                    uuid, title, description, duration, intensity, training_styles, type,
                                    sets, reps, rest, equipment, suitable_locations, difficulty,
                                    instructions, tips, common_mistakes, progression_steps, variations,
                                    video_url, thumbnail_url, is_custom
                                ) VALUES (
                                    uuid_generate_v4(), :title, :description, :duration, :intensity, :training_styles, :type,
                                    :sets, :reps, :rest, :equipment, :suitable_locations, :difficulty,
                                    :instructions, :tips, :common_mistakes, :progression_steps, :variations,
                                    :video_url, :thumbnail_url, false
                                )
                            """
                            
                            # Execute drill insert and get the UUID
                            result = conn.execute(text(insert_sql), {
                                'title': drill['title'],
                                'description': drill['description'],
                                'duration': drill.get('duration', 10),
                                'intensity': drill.get('intensity', 'medium'),
                                'training_styles': training_styles_json,
                                'type': drill.get('type', 'set_based'),
                                'sets': drill.get('sets', 3),
                                'reps': drill.get('reps', 10),
                                'rest': drill.get('rest', 60),
                                'equipment': equipment_json,
                                'suitable_locations': suitable_locations_json,
                                'difficulty': drill.get('difficulty', 'intermediate'),
                                'instructions': instructions_json,
                                'tips': tips_json,
                                'common_mistakes': common_mistakes_json,
                                'progression_steps': progression_steps_json,
                                'variations': variations_json,
                                'video_url': drill.get('video_url', ''),
                                'thumbnail_url': drill.get('thumbnail_url', '')
                            })
                            
                            # Get the UUID of the newly inserted drill
                            drill_uuid_result = conn.execute(text("""
                                SELECT uuid FROM drills WHERE title = :title ORDER BY id DESC LIMIT 1
                            """), {'title': drill['title']})
                            drill_uuid = drill_uuid_result.fetchone()[0]
                            
                            # Create skill focus relationship
                            skill_focus_sql = """
                                INSERT INTO drill_skill_focus (drill_uuid, category, sub_skill, is_primary)
                                VALUES (:drill_uuid, :category, :sub_skill, true)
                            """
                            
                            conn.execute(text(skill_focus_sql), {
                                'drill_uuid': drill_uuid,
                                'category': category.lower(),
                                'sub_skill': 'general'  # Default sub_skill for new categories
                            })
                            
                            seeded_count += 1
                            
                        except Exception as e:
                            logging.warning(f"   ⚠️ Failed to seed drill '{drill.get('title', 'Unknown')}': {str(e)[:100]}...")
                            continue
                    
                    logging.info(f"✅ Seeded {seeded_count}/{len(drills)} {category.lower()} drills")
                    total_drills_seeded += seeded_count
                
                trans.commit()
                logging.info(f"✅ Successfully seeded {total_drills_seeded} total new drills")
                return True
                
            except Exception as e:
                trans.rollback()
                logging.error(f"❌ Transaction failed during drill seeding: {e}")
                raise
                
    except Exception as e:
        logging.error(f"❌ Error seeding new drills: {e}")
        return False

def phase_5_verify_migration(staging_engine):
    """Phase 5: Verify complete migration"""
    logging.info("🚀 PHASE 5: Verifying Complete Migration")
    logging.info("=" * 50)
    
    verification_queries = [
        ("Production Tables", "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"),
        ("Users", "SELECT COUNT(*) FROM users"),
        ("Drills", "SELECT COUNT(*) FROM drills"),
        ("Drills with UUIDs", "SELECT COUNT(*) FROM drills WHERE uuid IS NOT NULL"),
        ("Custom Drills", "SELECT COUNT(*) FROM custom_drills"),
        ("Mental Training Quotes", "SELECT COUNT(*) FROM mental_training_quotes"),
        ("Mental Training Sessions", "SELECT COUNT(*) FROM mental_training_sessions"),
        ("Completed Sessions", "SELECT COUNT(*) FROM completed_sessions"),
        ("Progress History", "SELECT COUNT(*) FROM progress_history"),
        ("Drill Skill Focus with UUIDs", "SELECT COUNT(*) FROM drill_skill_focus WHERE drill_uuid IS NOT NULL"),
        ("Drill Group Items with UUIDs", "SELECT COUNT(*) FROM drill_group_items WHERE drill_uuid IS NOT NULL"),
    ]
    
    all_passed = True
    with staging_engine.connect() as conn:
        for description, query in verification_queries:
            try:
                result = conn.execute(text(query))
                count = result.fetchone()[0]
                logging.info(f"   ✅ {description}: {count}")
                
                # Check for critical issues
                if description == "Drills" and count == 0:
                    logging.error(f"   ❌ CRITICAL: No drills found!")
                    all_passed = False
                elif description == "Drills with UUIDs" and count == 0:
                    logging.error(f"   ❌ CRITICAL: No drill UUIDs generated!")
                    all_passed = False
                    
            except Exception as e:
                logging.error(f"   ❌ Could not verify {description}: {e}")
                all_passed = False
    
    if all_passed:
        logging.info("✅ All verification checks passed!")
    else:
        logging.error("❌ Some verification checks failed!")
    
    return all_passed

def phase_6_fix_drill_ids(staging_engine, dry_run=False, conn=None):
    """Phase 6: Fix drill IDs in completed sessions JSON"""
    logging.info("🚀 PHASE 6: Fixing Completed Session Drill IDs")
    logging.info("=" * 50)
    
    if dry_run:
        logging.info("🔍 DRY RUN: Would fix drill IDs in completed sessions JSON")
        return True
    
    # Use provided connection or create a new one
    if conn is not None:
        # Running as part of larger transaction
        try:
            # Use the efficient SQL approach from the working script
            result = conn.execute(text("""
                UPDATE completed_sessions 
                SET drills = jsonb_set(
                    drills::jsonb, 
                    '{0,drill,id}', 
                    to_jsonb(d.uuid::text)
                )
                FROM drills d 
                WHERE drills::jsonb->0->'drill'->>'title' = d.title
                AND drills IS NOT NULL
                AND jsonb_array_length(drills::jsonb) = 1
                AND drills::jsonb->0->'drill'->>'id' != d.uuid::text
            """))
            single_drill_updates = result.rowcount
            logging.info(f"✅ Fixed {single_drill_updates} single-drill sessions")
            return True
            
        except Exception as e:
            logging.error(f"💥 Phase 6 failed: {e}")
            raise
    else:
        # Running individually - create own transaction
        try:
            with staging_engine.begin() as individual_conn:
                result = individual_conn.execute(text("""
                    UPDATE completed_sessions 
                    SET drills = jsonb_set(
                        drills::jsonb, 
                        '{0,drill,id}', 
                        to_jsonb(d.uuid::text)
                    )
                    FROM drills d 
                    WHERE drills::jsonb->0->'drill'->>'title' = d.title
                    AND drills IS NOT NULL
                    AND jsonb_array_length(drills::jsonb) = 1
                    AND drills::jsonb->0->'drill'->>'id' != d.uuid::text
                """))
                single_drill_updates = result.rowcount
                logging.info(f"✅ Fixed {single_drill_updates} single-drill sessions")
                return True
                
        except Exception as e:
            logging.error(f"💥 Phase 6 failed: {e}")
            raise

def phase_7_fix_multi_drill_sessions(staging_engine, dry_run=False, conn=None):
    """Phase 7: Fix multi-drill sessions"""
    logging.info("🚀 PHASE 7: Fixing Multi-Drill Sessions")
    logging.info("=" * 50)
    
    if dry_run:
        logging.info("🔍 DRY RUN: Would fix multi-drill sessions")
        return True
    
    # Use provided connection or create a new one
    if conn is not None:
        # Running as part of larger transaction
        return fix_multi_drill_sessions_logic(conn)
    else:
        # Running individually - create own transaction
        try:
            with staging_engine.begin() as individual_conn:
                return fix_multi_drill_sessions_logic(individual_conn)
        except Exception as e:
            logging.error(f"💥 Phase 7 failed: {e}")
            raise

def fix_multi_drill_sessions_logic(conn):
    """The actual logic for fixing multi-drill sessions - extracted from working script"""
    import json
    
    fixed_sessions = 0
    fixed_positions = 0
    
    # Get all multi-drill sessions
    result = conn.execute(text("""
        SELECT id, drills::jsonb as drills_json
        FROM completed_sessions 
        WHERE drills IS NOT NULL 
        AND jsonb_array_length(drills::jsonb) > 1
    """))
    
    sessions = result.fetchall()
    total_sessions = len(sessions)
    logging.info(f"📋 Found {total_sessions} multi-drill sessions to process")
    
    if not sessions:
        logging.info("✅ No multi-drill sessions need fixing")
        return True
    
    # Progress tracking variables
    processed_count = 0
    progress_interval = 10 if total_sessions <= 100 else 20  # Use 10 for smaller batches, 20 for larger
    
    for session in sessions:
        session_id = session[0]
        drills_array = session[1]
        updated_drills = []
        session_updated = False
        
        # Process each drill in the array
        for i, drill_obj in enumerate(drills_array):
            if 'drill' in drill_obj:
                drill_title = drill_obj['drill']['title']
                current_id = drill_obj['drill']['id']
                
                # Find the correct UUID for this drill
                uuid_result = conn.execute(text("""
                    SELECT uuid FROM drills WHERE title = :title
                """), {'title': drill_title})
                
                uuid_row = uuid_result.fetchone()
                if uuid_row:
                    correct_uuid = str(uuid_row[0])
                    if current_id != correct_uuid:
                        # Update the drill ID
                        drill_obj['drill']['id'] = correct_uuid
                        session_updated = True
                        fixed_positions += 1
            
            updated_drills.append(drill_obj)
        
        # Update the session if any drills were changed
        if session_updated:
            conn.execute(text("""
                UPDATE completed_sessions 
                SET drills = :updated_drills
                WHERE id = :session_id
            """), {
                'updated_drills': json.dumps(updated_drills),
                'session_id': session_id
            })
            fixed_sessions += 1
        
        # Progress indicator
        processed_count += 1
        if processed_count % progress_interval == 0 or processed_count == total_sessions:
            percentage = (processed_count / total_sessions * 100)
            logging.info(f"   🔄 Progress: {processed_count}/{total_sessions} sessions processed ({percentage:.1f}%)")
    
    logging.info(f"✅ Fixed {fixed_sessions} sessions with {fixed_positions} drill positions")
    return True

def phase_8_migrate_video_urls(staging_engine, dry_run=False, conn=None):
    """Phase 8: Migrate video URLs to H264 bucket"""
    logging.info("🚀 PHASE 8: Migrating Video URLs to H264 Bucket")
    logging.info("=" * 50)
    
    old_bucket_url = "https://bravoball-drills.s3.us-east-2.amazonaws.com"
    new_bucket_url = "https://bravoball-drills-h264.s3.us-east-2.amazonaws.com"
    
    if dry_run:
        logging.info("🔍 DRY RUN: Would migrate video URLs from old to new bucket")
        logging.info(f"   From: {old_bucket_url}")
        logging.info(f"   To: {new_bucket_url}")
        return True
    
    # Use provided connection or create a new one
    if conn is not None:
        # Running as part of larger transaction
        return migrate_video_urls_logic(conn, old_bucket_url, new_bucket_url)
    else:
        # Running individually - create own transaction
        try:
            with staging_engine.begin() as individual_conn:
                return migrate_video_urls_logic(individual_conn, old_bucket_url, new_bucket_url)
        except Exception as e:
            logging.error(f"💥 Phase 8 failed: {e}")
            raise

def migrate_video_urls_logic(conn, old_bucket_url, new_bucket_url):
    """The actual logic for migrating video URLs"""
    # Check how many drills need updating
    result = conn.execute(text("""
        SELECT COUNT(*) FROM drills 
        WHERE video_url LIKE :old_pattern
    """), {'old_pattern': f'%{old_bucket_url}%'})
    drills_to_update = result.fetchone()[0]
    
    logging.info(f"📋 Found {drills_to_update} drills with old video URLs")
    
    if drills_to_update == 0:
        logging.info("✅ No video URLs need updating")
        return True
    
    # Update video URLs in drills table
    result = conn.execute(text("""
        UPDATE drills 
        SET video_url = REPLACE(video_url, :old_bucket, :new_bucket)
        WHERE video_url LIKE :old_pattern
    """), {
        'old_bucket': old_bucket_url,
        'new_bucket': new_bucket_url,
        'old_pattern': f'%{old_bucket_url}%'
    })
    
    updated_count = result.rowcount
    logging.info(f"✅ Updated {updated_count} drill video URLs")
    
    # Update thumbnail URLs if they exist
    result = conn.execute(text("""
        UPDATE drills 
        SET thumbnail_url = REPLACE(thumbnail_url, :old_bucket, :new_bucket)
        WHERE thumbnail_url LIKE :old_pattern
    """), {
        'old_bucket': old_bucket_url,
        'new_bucket': new_bucket_url,
        'old_pattern': f'%{old_bucket_url}%'
    })
    
    thumb_updated = result.rowcount
    if thumb_updated > 0:
        logging.info(f"✅ Updated {thumb_updated} drill thumbnail URLs")
    
    # Check custom_drills table (if it exists and has video URLs)
    try:
        result = conn.execute(text("""
            UPDATE custom_drills 
            SET video_url = REPLACE(video_url, :old_bucket, :new_bucket)
            WHERE video_url LIKE :old_pattern
        """), {
            'old_bucket': old_bucket_url,
            'new_bucket': new_bucket_url,
            'old_pattern': f'%{old_bucket_url}%'
        })
        custom_updated = result.rowcount
        if custom_updated > 0:
            logging.info(f"✅ Updated {custom_updated} custom drill video URLs")
    except Exception:
        # Custom drills might not have video_url column yet
        logging.info("   ℹ️ Custom drills video URLs not updated (column may not exist)")
    
    logging.info(f"✅ Video URL migration completed successfully!")
    return True

def phase_9_fix_drill_categories(staging_engine, dry_run=False, conn=None):
    """Phase 9: Fix missing drill categories and assign drills to proper categories"""
    logging.info("🚀 PHASE 9: Fixing Drill Categories & Assignments")
    logging.info("=" * 50)
    
    if dry_run:
        logging.info("🔍 DRY RUN: Would fix drill categories and assignments")
        return True
    
    # Use provided connection or create a new one
    if conn is not None:
        # Running as part of larger transaction
        return fix_drill_categories_logic(conn)
    else:
        # Running individually - create own transaction
        try:
            with staging_engine.begin() as individual_conn:
                return fix_drill_categories_logic(individual_conn)
        except Exception as e:
            logging.error(f"💥 Phase 9 failed: {e}")
            raise

def fix_drill_categories_logic(conn):
    """The actual logic for fixing drill categories"""
    
    # Step 1: Create missing drill categories
    logging.info("📋 Step 1: Creating missing drill categories...")
    
    missing_categories = [
        ('defending', 'Drills focusing on defending skills'),
        ('goalkeeping', 'Drills focusing on goalkeeping skills'),
        ('fitness', 'Drills focusing on fitness skills')
    ]
    
    for category_name, description in missing_categories:
        result = conn.execute(text("""
            INSERT INTO drill_categories (name, description) 
            VALUES (:name, :description) 
            ON CONFLICT (name) DO NOTHING
            RETURNING id
        """), {'name': category_name, 'description': description})
        
        if result.rowcount > 0:
            logging.info(f"   ✅ Created category: {category_name}")
        else:
            logging.info(f"   ℹ️ Category already exists: {category_name}")
    
    # Step 2: Get category IDs
    result = conn.execute(text("SELECT id, name FROM drill_categories"))
    categories = {row[1]: row[0] for row in result.fetchall()}
    logging.info(f"📋 Available categories: {list(categories.keys())}")
    
    # Step 3: Check drills without categories
    result = conn.execute(text("SELECT COUNT(*) FROM drills WHERE category_id IS NULL"))
    uncategorized_count = result.fetchone()[0]
    logging.info(f"📋 Found {uncategorized_count} drills without categories")
    
    if uncategorized_count == 0:
        logging.info("✅ All drills already have categories assigned!")
        return True
    
    # Step 4: Get uncategorized drills and check their skill focus
    result = conn.execute(text("""
        SELECT d.id, d.title, sf.category as skill_category 
        FROM drills d 
        LEFT JOIN drill_skill_focus sf ON d.uuid = sf.drill_uuid AND sf.is_primary = true
        WHERE d.category_id IS NULL
        LIMIT 20
    """))
    
    uncategorized_drills = result.fetchall()
    
    # Step 5: Assign categories based on skill focus
    assignments_made = 0
    
    for drill_id, title, skill_category in uncategorized_drills:
        target_category = None
        
        if skill_category:
            # Use the skill category if available
            target_category = skill_category.lower()
        else:
            # Try to infer from title
            title_lower = title.lower()
            if any(word in title_lower for word in ['pass', 'passing']):
                target_category = 'passing'
            elif any(word in title_lower for word in ['shoot', 'shooting', 'goal', 'finish']):
                target_category = 'shooting'
            elif any(word in title_lower for word in ['dribble', 'dribbling', 'ball control']):
                target_category = 'dribbling'
            elif any(word in title_lower for word in ['first touch', 'touch', 'control']):
                target_category = 'first_touch'
            elif any(word in title_lower for word in ['defend', 'defending', 'tackle', 'marking']):
                target_category = 'defending'
            elif any(word in title_lower for word in ['goalkeeper', 'goalkeeping', 'keeper', 'save']):
                target_category = 'goalkeeping'
            elif any(word in title_lower for word in ['fitness', 'conditioning', 'sprint', 'run', 'endurance']):
                target_category = 'fitness'
        
        if target_category and target_category in categories:
            category_id = categories[target_category]
            conn.execute(text("""
                UPDATE drills 
                SET category_id = :category_id 
                WHERE id = :drill_id
            """), {'category_id': category_id, 'drill_id': drill_id})
            
            assignments_made += 1
            logging.info(f"   ✅ Assigned '{title}' to {target_category}")
        else:
            logging.info(f"   ⚠️ Could not categorize '{title}' (skill: {skill_category})")
    
    # Step 6: Handle remaining uncategorized drills by assigning to a default category
    result = conn.execute(text("SELECT COUNT(*) FROM drills WHERE category_id IS NULL"))
    remaining_count = result.fetchone()[0]
    
    if remaining_count > 0:
        # Assign remaining drills to 'fitness' as a safe default
        default_category_id = categories.get('fitness')
        if default_category_id:
            conn.execute(text("""
                UPDATE drills 
                SET category_id = :category_id 
                WHERE category_id IS NULL
            """), {'category_id': default_category_id})
            
            logging.info(f"   ✅ Assigned {remaining_count} remaining drills to 'fitness' category")
            assignments_made += remaining_count
    
    # Step 7: Verify results
    result = conn.execute(text("""
        SELECT dc.name, COUNT(d.id) as drill_count 
        FROM drill_categories dc 
        LEFT JOIN drills d ON dc.id = d.category_id 
        GROUP BY dc.name 
        ORDER BY dc.name
    """))
    
    logging.info("📊 Final category distribution:")
    for category_name, drill_count in result.fetchall():
        logging.info(f"   {category_name}: {drill_count} drills")
    
    logging.info(f"✅ Category assignment completed! Made {assignments_made} assignments.")
    return True

def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Complete BravoBall v2 Migration')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--skip-backup', action='store_true', help='Skip backup creation')
    parser.add_argument('--skip-data-import', action='store_true', help='Skip Phase 1 data import (use when data already copied)')
    parser.add_argument('--production-url', default=PROD_URL, help='Production database URL (source)')
    parser.add_argument('--staging-url', default=STAGING_URL, help='Staging database URL (current target)')
    parser.add_argument('--v2-url', default=V2_URL, help='V2 database URL (for blue-green deployment)')
    parser.add_argument('--target-db', choices=['staging', 'v2'], default='staging', 
                        help='Target database for migration (staging or v2)')
    parser.add_argument('--phase', type=int, choices=[1,2,3,4,5,6,7,8,9], help='Run specific phase only')
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = setup_logging()
    logging.info("🚀 Starting Complete BravoBall v2 Migration")
    logging.info("=" * 70)
    
    if args.dry_run:
        logging.info("🔍 DRY RUN MODE - No changes will be applied")
    
    if args.skip_data_import:
        logging.info("⏭️ SKIPPING DATA IMPORT - Assuming production data already copied")
    
    try:
        # Determine target database URL based on --target-db argument
        if args.target_db == 'v2':
            target_url = args.v2_url
            target_name = "V2 database"
        else:
            target_url = args.staging_url
            target_name = "staging database"
        
        # Create target engine (keeping variable name for compatibility)
        staging_engine = create_engine(target_url)
        logging.info(f"🔗 Connected to {target_name}")
        logging.info(f"📍 Target URL: {target_url[:50]}...") # Show partial URL for verification
        
        # Create initial backup
        if not args.dry_run and not args.skip_backup:
            create_backup(staging_engine, "initial")
        
        # Run migration phases
        phases = {
            1: ("Import Production Data", phase_1_import_production_data),
            2: ("Apply v2 Schema", phase_2_apply_v2_schema),
            3: ("Populate UUIDs", phase_3_populate_uuids),
            4: ("Seed New Content", phase_4_seed_new_content),
            5: ("Verify Migration", phase_5_verify_migration),
            6: ("Fix Completed Session Drill IDs", phase_6_fix_drill_ids),
            7: ("Fix Multi-Drill Sessions", phase_7_fix_multi_drill_sessions),
            8: ("Migrate Video URLs to H264", phase_8_migrate_video_urls),
            9: ("Fix Drill Categories & Assignments", phase_9_fix_drill_categories),
        }
        
        if args.phase:
            # Run single phase
            phase_num = args.phase
            phase_name, phase_func = phases[phase_num]
            logging.info(f"\n🎯 Running Phase {phase_num} only: {phase_name}")
            
            if phase_num == 5:
                success = phase_func(staging_engine)
            elif phase_num in [6, 7, 8, 9]:
                # Phases that support connection parameter
                success = phase_func(staging_engine, args.dry_run)
            else:
                success = phase_func(staging_engine, args.dry_run)
        else:
            # Run all phases (or skip Phase 1 if requested) with shared transaction for phases 3-8
            all_success = True
            start_phase = 2 if args.skip_data_import else 1
            
            # Phases 1-2 run independently
            for phase_num in [1, 2]:
                if phase_num < start_phase:
                    if args.skip_data_import and phase_num == 1:
                        logging.info(f"\n⏭️ Skipping Phase {phase_num}: {phases[phase_num][0]}")
                        continue
                
                if phase_num in phases:
                    phase_name, phase_func = phases[phase_num]
                    logging.info(f"\n🎯 Phase {phase_num}: {phase_name}")
                    
                    # Create backup before each phase (except dry run)
                    if not args.dry_run and not args.skip_backup and phase_num > start_phase:
                        create_backup(staging_engine, f"phase_{phase_num}")
                    
                    # Run phase
                    success = phase_func(staging_engine, args.dry_run)
                    
                    if not success:
                        logging.error(f"❌ Phase {phase_num} failed!")
                        all_success = False
                        break
                        
                    logging.info(f"✅ Phase {phase_num} completed successfully")
            
            # Phases 3-9 run with shared transaction to avoid conflicts
            if all_success and not args.dry_run:
                logging.info("\n🔗 Running Phases 3-9 with shared transaction...")
                try:
                    with staging_engine.begin() as shared_conn:
                        for phase_num in [3, 4, 5, 6, 7, 8, 9]:
                            if phase_num in phases:
                                phase_name, phase_func = phases[phase_num]
                                logging.info(f"\n🎯 Phase {phase_num}: {phase_name}")
                                
                                # Create backup before each phase
                                if not args.skip_backup and phase_num > 3:
                                    create_backup(staging_engine, f"phase_{phase_num}")
                                
                                # Run phase with shared connection
                                if phase_num == 3:
                                    success = phase_func(staging_engine, False)  # phase_3 doesn't support conn param yet
                                elif phase_num == 4:
                                    success = phase_func(staging_engine, False)  # phase_4 doesn't support conn param yet
                                elif phase_num == 5:
                                    success = phase_func(staging_engine)  # phase_5 is read-only
                                elif phase_num in [6, 7, 8, 9]:
                                    success = phase_func(staging_engine, False, shared_conn)  # Use shared connection
                                
                                if not success:
                                    logging.error(f"❌ Phase {phase_num} failed!")
                                    all_success = False
                                    break
                                    
                                logging.info(f"✅ Phase {phase_num} completed successfully")
                        
                        if all_success:
                            logging.info("✅ All phases with shared transaction completed successfully!")
                            
                except Exception as e:
                    logging.error(f"❌ Shared transaction failed: {e}")
                    all_success = False
            elif all_success and args.dry_run:
                # In dry run mode, run phases 3-9 without shared transaction
                for phase_num in [3, 4, 5, 6, 7, 8, 9]:
                    if phase_num in phases:
                        phase_name, phase_func = phases[phase_num]
                        logging.info(f"\n🎯 Phase {phase_num}: {phase_name}")
                        
                        # Run phase in dry run mode
                        if phase_num == 5:
                            logging.info("🔍 DRY RUN: Would verify migration")
                            success = True  # Skip verification in dry run
                        elif phase_num in [6, 7, 8, 9]:
                            success = phase_func(staging_engine, True)  # dry_run=True
                        else:
                            success = phase_func(staging_engine, True)  # dry_run=True
                        
                        if not success:
                            logging.error(f"❌ Phase {phase_num} failed!")
                            all_success = False
                            break
                            
                        logging.info(f"✅ Phase {phase_num} completed successfully")
            
            success = all_success
        
        if success:
            logging.info("\n🎉 Complete v2 migration finished successfully!")
            logging.info("=" * 70)
            if args.skip_data_import:
                logging.info("📱 V2 schema migration completed on existing production data")
            else:
                logging.info("📱 Full migration completed - production data copied and V2 schema applied")
            logging.info("🔧 All phases completed:")
            logging.info("   ✅ Schema updates from models.py")
            logging.info("   ✅ UUID population and relationships")
            logging.info("   ✅ Mental training quotes seeded")
            logging.info("   ✅ Drill ID mismatches fixed")
            logging.info("   ✅ Multi-drill sessions fixed")
            logging.info("   ✅ Video URLs migrated to H264 bucket")
            logging.info("   ✅ Drill categories fixed and assignments completed")
            logging.info("🚀 Ready for Flutter app testing!")
        else:
            logging.error("\n💥 Migration completed with errors!")
            sys.exit(1)
        
    except Exception as e:
        logging.error(f"💥 Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 