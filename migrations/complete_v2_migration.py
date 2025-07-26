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
"""

import json
import os
import sys
import logging
import subprocess
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Database URLs
PROD_URL = 'postgresql://jordan:nznEGcxVZbVyX5PvYXG5LuVQ15v0Tsd5@dpg-d11nbs3ipnbc73d2e2f0-a.oregon-postgres.render.com/bravoballdb'
STAGING_URL = 'postgresql://bravoball_staging_db_user:DszQQ1qg7XH2ocCNSCU844S43SMU4G4V@dpg-d21l5oh5pdvs7382nib0-a.oregon-postgres.render.com/bravoball_staging_db'

def setup_logging():
    """Setup logging for migration"""
    log_filename = f"complete_v2_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    """Create database backup before each major phase"""
    backup_filename = f"backup_{phase_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
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
    """Phase 2: Apply v2 schema changes carefully"""
    logging.info("🚀 PHASE 2: Applying v2 Schema Changes")
    logging.info("=" * 50)
    
    # Define v2 schema changes
    schema_changes = [
        # Enable UUID extension
        'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
        
        # Create new v2 tables
        '''CREATE TABLE IF NOT EXISTS mental_training_quotes (
            id SERIAL PRIMARY KEY,
            content VARCHAR NOT NULL,
            author VARCHAR NOT NULL,
            type VARCHAR NOT NULL,
            display_duration INTEGER,
            created_at TIMESTAMP DEFAULT NOW()
        )''',
        
        '''CREATE TABLE IF NOT EXISTS custom_drills (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            title VARCHAR NOT NULL,
            skill VARCHAR NOT NULL,
            sub_skills TEXT[],
            sets INTEGER DEFAULT 1,
            reps INTEGER DEFAULT 1,
            duration INTEGER DEFAULT 0,
            description TEXT,
            instructions TEXT[],
            tips TEXT[],
            equipment TEXT[],
            training_style VARCHAR DEFAULT 'technical',
            difficulty VARCHAR DEFAULT 'beginner',
            uuid UUID DEFAULT uuid_generate_v4() NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )''',
        
        '''CREATE TABLE IF NOT EXISTS mental_training_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            duration_minutes INTEGER NOT NULL,
            completed_at TIMESTAMP DEFAULT NOW(),
            quotes_shown TEXT[],
            session_notes TEXT
        )''',
        
        '''CREATE TABLE IF NOT EXISTS email_verification_codes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            code VARCHAR NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT NOW()
        )''',
        
        # Add new columns to existing tables
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS dribbling_drills_completed INTEGER DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS drills_per_session DOUBLE PRECISION DEFAULT 0.0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS shooting_drills_completed INTEGER DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS fitness_drills_completed INTEGER DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS mental_training_sessions INTEGER DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS beginner_drills_completed INTEGER DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS most_improved_skill VARCHAR DEFAULT \'\'',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS previous_streak INTEGER DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS defending_drills_completed INTEGER DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS first_touch_drills_completed INTEGER DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS minutes_per_session DOUBLE PRECISION DEFAULT 0.0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS total_mental_training_minutes INTEGER DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS passing_drills_completed INTEGER DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS advanced_drills_completed INTEGER DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS total_time_all_sessions INTEGER DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS intermediate_drills_completed INTEGER DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS unique_drills_completed INTEGER DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS goalkeeping_drills_completed INTEGER DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS favorite_drill VARCHAR DEFAULT \'\'',
        
        # Add UUID and custom drill columns to drills table
        'ALTER TABLE drills ADD COLUMN IF NOT EXISTS is_custom BOOLEAN DEFAULT false',
        'ALTER TABLE drills ADD COLUMN IF NOT EXISTS uuid UUID DEFAULT uuid_generate_v4() NOT NULL',
        
        # Add UUID columns to foreign key tables
        'ALTER TABLE drill_skill_focus ADD COLUMN IF NOT EXISTS drill_uuid UUID',
        'ALTER TABLE drill_group_items ADD COLUMN IF NOT EXISTS drill_uuid UUID',
        'ALTER TABLE ordered_session_drills ADD COLUMN IF NOT EXISTS drill_uuid UUID',
        
        # Add mental training columns to completed_sessions
        'ALTER TABLE completed_sessions ADD COLUMN IF NOT EXISTS session_type VARCHAR DEFAULT \'drill\'',
        'ALTER TABLE completed_sessions ADD COLUMN IF NOT EXISTS duration_minutes INTEGER DEFAULT 0',
        'ALTER TABLE completed_sessions ADD COLUMN IF NOT EXISTS mental_training_session_id INTEGER',
    ]
    
    logging.info(f"📋 Schema migration contains {len(schema_changes)} statements")
    
    if dry_run:
        logging.info("🔍 DRY RUN: Would apply v2 schema changes")
        for i, stmt in enumerate(schema_changes, 1):
            logging.info(f"   Would execute {i}: {stmt[:80]}...")
        return True
    
    # Apply schema changes
    with staging_engine.connect() as conn:
        trans = conn.begin()
        try:
            for i, stmt in enumerate(schema_changes, 1):
                logging.info(f"   Executing {i}/{len(schema_changes)}: {stmt[:80]}...")
                conn.execute(text(stmt))
            
            trans.commit()
            logging.info("✅ V2 schema changes applied successfully")
            return True
            
        except Exception as e:
            trans.rollback()
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
            
            # 2. Update foreign key tables to include drill_uuid
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
                
                logging.info(f"🔗 Updating {table} with drill UUIDs...")
                try:
                    result = conn.execute(text(query))
                    updated_count = result.rowcount
                    logging.info(f"   ✅ Updated {updated_count} records in {table}")
                except Exception as e:
                    logging.warning(f"   ⚠️ Could not update {table}: {e}")
            
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
            
            trans.commit()
            logging.info("✅ UUID population completed successfully")
            return True
            
        except Exception as e:
            trans.rollback()
            logging.error(f"❌ UUID population failed: {e}")
            raise

def phase_4_seed_mental_training_quotes(staging_engine, dry_run=False):
    """Phase 4: Seed mental training quotes"""
    logging.info("🚀 PHASE 4: Seeding Mental Training Quotes")
    logging.info("=" * 50)
    
    # Get quotes file
    quotes_file = os.path.join(os.path.dirname(__file__), '..', 'drills', 'mental_training_quotes.txt')
    
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
                if "Drills" in description and count == 0:
                    logging.error(f"   ❌ CRITICAL: No drills found!")
                    all_passed = False
                elif "UUIDs" in description and "Drills with UUIDs" in description and count == 0:
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

def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Complete BravoBall v2 Migration')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--skip-backup', action='store_true', help='Skip backup creation')
    parser.add_argument('--skip-data-import', action='store_true', help='Skip Phase 1 data import (use when data already copied)')
    parser.add_argument('--staging-url', default=STAGING_URL, help='Staging database URL')
    parser.add_argument('--phase', type=int, choices=[1,2,3,4,5], help='Run specific phase only')
    
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
        # Create staging engine
        staging_engine = create_engine(args.staging_url)
        logging.info(f"🔗 Connected to staging database")
        
        # Create initial backup
        if not args.dry_run and not args.skip_backup:
            create_backup(staging_engine, "initial")
        
        # Run migration phases
        phases = {
            1: ("Import Production Data", phase_1_import_production_data),
            2: ("Apply v2 Schema", phase_2_apply_v2_schema),
            3: ("Populate UUIDs", phase_3_populate_uuids),
            4: ("Seed Mental Training Quotes", phase_4_seed_mental_training_quotes),
            5: ("Verify Migration", phase_5_verify_migration),
        }
        
        if args.phase:
            # Run single phase
            phase_num = args.phase
            phase_name, phase_func = phases[phase_num]
            logging.info(f"\n🎯 Running Phase {phase_num} only: {phase_name}")
            
            if phase_num == 5:
                success = phase_func(staging_engine)
            else:
                success = phase_func(staging_engine, args.dry_run)
        else:
            # Run all phases (or skip Phase 1 if requested)
            all_success = True
            start_phase = 2 if args.skip_data_import else 1
            
            for phase_num, (phase_name, phase_func) in phases.items():
                if phase_num < start_phase:
                    if args.skip_data_import and phase_num == 1:
                        logging.info(f"\n⏭️ Skipping Phase {phase_num}: {phase_name}")
                        continue
                
                logging.info(f"\n🎯 Phase {phase_num}: {phase_name}")
                
                # Create backup before each phase (except dry run)
                if not args.dry_run and not args.skip_backup and phase_num > start_phase:
                    create_backup(staging_engine, f"phase_{phase_num}")
                
                # Run phase
                if phase_num == 5:
                    success = phase_func(staging_engine)
                else:
                    success = phase_func(staging_engine, args.dry_run)
                
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
            logging.info("🔧 Next steps:")
            logging.info("   1. Test Flutter app with staging")
            logging.info("   2. Verify all features work correctly")
            logging.info("   3. Apply same migration to production")
        else:
            logging.error("\n💥 Migration completed with errors!")
            sys.exit(1)
        
    except Exception as e:
        logging.error(f"💥 Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 