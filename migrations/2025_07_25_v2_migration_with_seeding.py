#!/usr/bin/env python3
"""
Complete BravoBall v2 Migration with Mental Training Quotes Seeding
Date: 2025-07-25
Purpose: Apply all v2 schema changes AND seed mental training quotes
"""

import json
import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def setup_logging():
    """Setup logging for migration"""
    log_filename = f"v2_migration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_filename

def backup_database(engine):
    """Create database backup before migration"""
    backup_filename = f"v2_migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    database_url = str(engine.url)
    
    logging.info(f"Creating backup: {backup_filename}")
    
    import subprocess
    try:
        result = subprocess.run([
            'pg_dump', database_url, '--no-owner', '--no-privileges'
        ], capture_output=True, text=True, check=True)
        
        with open(backup_filename, 'w') as f:
            f.write(result.stdout)
        
        logging.info(f"✅ Backup created: {backup_filename}")
        return backup_filename
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Backup failed: {e}")
        raise

def run_v2_schema_migration(engine, dry_run=False):
    """Apply all v2 schema changes"""
    
    # Define all v2 migration statements
    migration_statements = [
        # Enable uuid extension
        'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
        
        # Create new v2 tables
        '''CREATE TABLE IF NOT EXISTS mental_training_quotes (
            id integer NOT NULL,
            content character varying NOT NULL,
            author character varying NOT NULL,
            type character varying NOT NULL,
            display_duration integer,
            created_at timestamp without time zone DEFAULT now()
        )''',
        
        '''CREATE TABLE IF NOT EXISTS custom_drills (
            id integer NOT NULL,
            user_id integer,
            title character varying NOT NULL,
            skill character varying NOT NULL,
            sub_skills text[],
            sets integer DEFAULT 1,
            reps integer DEFAULT 1,
            duration integer DEFAULT 0,
            description text,
            instructions text[],
            tips text[],
            equipment text[],
            training_style character varying DEFAULT 'technical',
            difficulty character varying DEFAULT 'beginner',
            uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL,
            created_at timestamp without time zone DEFAULT now(),
            updated_at timestamp without time zone DEFAULT now()
        )''',
        
        '''CREATE TABLE IF NOT EXISTS mental_training_sessions (
            id integer NOT NULL,
            user_id integer,
            duration_minutes integer NOT NULL,
            completed_at timestamp without time zone DEFAULT now(),
            quotes_shown text[],
            session_notes text
        )''',
        
        '''CREATE TABLE IF NOT EXISTS email_verification_codes (
            id integer NOT NULL,
            user_id integer,
            code character varying NOT NULL,
            expires_at timestamp without time zone NOT NULL,
            used boolean DEFAULT false,
            created_at timestamp without time zone DEFAULT now()
        )''',
        
        # Add new columns to existing tables
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS dribbling_drills_completed integer DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS drills_per_session double precision DEFAULT 0.0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS shooting_drills_completed integer DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS fitness_drills_completed integer DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS mental_training_sessions integer DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS beginner_drills_completed integer DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS most_improved_skill character varying DEFAULT \'\'::character varying',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS previous_streak integer DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS defending_drills_completed integer DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS first_touch_drills_completed integer DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS minutes_per_session double precision DEFAULT 0.0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS total_mental_training_minutes integer DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS passing_drills_completed integer DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS advanced_drills_completed integer DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS total_time_all_sessions integer DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS intermediate_drills_completed integer DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS unique_drills_completed integer DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS goalkeeping_drills_completed integer DEFAULT 0',
        'ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS favorite_drill character varying DEFAULT \'\'::character varying',
        
        # Add UUID columns to existing tables
        'ALTER TABLE drills ADD COLUMN IF NOT EXISTS is_custom boolean DEFAULT false',
        'ALTER TABLE drills ADD COLUMN IF NOT EXISTS uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL',
        'ALTER TABLE drill_skill_focus ADD COLUMN IF NOT EXISTS drill_uuid uuid',
        'ALTER TABLE drill_group_items ADD COLUMN IF NOT EXISTS drill_uuid uuid',
        'ALTER TABLE ordered_session_drills ADD COLUMN IF NOT EXISTS drill_uuid uuid',
        
        # Add mental training columns to completed_sessions
        'ALTER TABLE completed_sessions ADD COLUMN IF NOT EXISTS session_type character varying DEFAULT \'drill\'::character varying',
        'ALTER TABLE completed_sessions ADD COLUMN IF NOT EXISTS duration_minutes integer DEFAULT 0',
        'ALTER TABLE completed_sessions ADD COLUMN IF NOT EXISTS mental_training_session_id integer',
    ]
    
    logging.info(f"V2 Migration contains {len(migration_statements)} SQL statements")
    
    if dry_run:
        logging.info("🔍 DRY RUN MODE - No changes will be applied")
        for i, stmt in enumerate(migration_statements, 1):
            logging.info(f"Would execute {i}: {stmt[:80]}...")
        return True
    
    # Execute migration statements
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            for i, stmt in enumerate(migration_statements, 1):
                logging.info(f"Executing {i}/{len(migration_statements)}: {stmt[:80]}...")
                conn.execute(text(stmt))
            
            trans.commit()
            logging.info("✅ V2 schema migration completed successfully")
            return True
            
        except Exception as e:
            trans.rollback()
            logging.error(f"❌ V2 migration failed: {e}")
            raise

def seed_mental_training_quotes(engine, dry_run=False):
    """Seed mental training quotes from JSON file"""
    logging.info("🌱 Starting mental training quotes seeding...")
    
    try:
        # Get the path to the quotes file
        quotes_file = os.path.join(os.path.dirname(__file__), '..', 'drills', 'mental_training_quotes.txt')
        
        with open(quotes_file, 'r', encoding='utf-8') as f:
            quotes = json.load(f)
        
        logging.info(f"✅ Loaded {len(quotes)} quotes from file")
        
        if dry_run:
            logging.info(f"🔍 DRY RUN: Would seed {len(quotes)} mental training quotes")
            for i, quote in enumerate(quotes[:3], 1):
                logging.info(f"  Quote {i}: \"{quote['content'][:60]}...\" - {quote['author']}")
            if len(quotes) > 3:
                logging.info(f"  ... and {len(quotes) - 3} more quotes")
            return True
        
        with engine.connect() as conn:
            # Check if quotes already exist
            result = conn.execute(text("SELECT COUNT(*) FROM mental_training_quotes"))
            existing_count = result.fetchone()[0]
            
            if existing_count > 0:
                logging.info(f"📋 Found {existing_count} existing quotes, skipping seeding")
                return True
            
            # Create sequence for mental_training_quotes
            conn.execute(text('CREATE SEQUENCE IF NOT EXISTS mental_training_quotes_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1'))
            conn.execute(text('ALTER TABLE mental_training_quotes ALTER COLUMN id SET DEFAULT nextval(\'mental_training_quotes_id_seq\'::regclass)'))
            
            # Insert quotes
            insert_sql = """
            INSERT INTO mental_training_quotes (id, content, author, type, display_duration, created_at)
            VALUES (:id, :content, :author, :type, :display_duration, NOW())
            """
            
            success_count = 0
            for i, quote in enumerate(quotes, 1):
                try:
                    conn.execute(text(insert_sql), {
                        'id': i,
                        'content': quote['content'],
                        'author': quote['author'],
                        'type': quote['type'],
                        'display_duration': quote['display_duration']
                    })
                    success_count += 1
                    
                    if i % 10 == 0:
                        logging.info(f"📝 Seeded {i}/{len(quotes)} quotes...")
                        
                except Exception as e:
                    logging.error(f"❌ Error seeding quote {i}: {e}")
            
            # Update the sequence
            conn.execute(text("SELECT setval('mental_training_quotes_id_seq', :max_id, true)"), {'max_id': len(quotes)})
            
            conn.commit()
            logging.info(f"✅ Successfully seeded {success_count}/{len(quotes)} mental training quotes")
            
            return success_count == len(quotes)
            
    except Exception as e:
        logging.error(f"❌ Error seeding mental training quotes: {e}")
        return False

def verify_migration(engine):
    """Verify migration was applied correctly"""
    logging.info("🔍 Verifying v2 migration...")
    
    verification_queries = [
        ("Tables", "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"),
        ("Mental Training Quotes", "SELECT COUNT(*) FROM mental_training_quotes"),
        ("Custom Drills", "SELECT COUNT(*) FROM custom_drills"), 
        ("Mental Training Sessions", "SELECT COUNT(*) FROM mental_training_sessions"),
        ("Email Verification Codes", "SELECT COUNT(*) FROM email_verification_codes"),
    ]
    
    with engine.connect() as conn:
        for description, query in verification_queries:
            try:
                result = conn.execute(text(query))
                count = result.fetchone()[0]
                logging.info(f"✅ {description}: {count}")
            except Exception as e:
                logging.warning(f"⚠️ Could not verify {description}: {e}")
    
    logging.info("✅ Migration verification completed")

def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Complete BravoBall v2 Migration with Seeding')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--database-url', help='Custom database URL')
    parser.add_argument('--skip-backup', action='store_true', help='Skip backup creation')
    parser.add_argument('--skip-seeding', action='store_true', help='Skip mental training quotes seeding')
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = setup_logging()
    logging.info("🚀 Starting Complete BravoBall v2 Migration")
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Get database URL
        database_url = args.database_url or os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL not found in environment or arguments")
        
        # Create engine
        engine = create_engine(database_url)
        logging.info(f"🔗 Connected to database")
        
        # Create backup (unless skipped or dry run)
        backup_file = None
        if not args.dry_run and not args.skip_backup:
            backup_file = backup_database(engine)
        
        # Run v2 schema migration
        schema_success = run_v2_schema_migration(engine, dry_run=args.dry_run)
        if not schema_success:
            raise Exception("Schema migration failed")
        
        # Seed mental training quotes (unless skipped)
        if not args.skip_seeding:
            seeding_success = seed_mental_training_quotes(engine, dry_run=args.dry_run)
            if not seeding_success:
                logging.warning("⚠️ Mental training quotes seeding had issues")
        
        # Verify migration (unless dry run)
        if not args.dry_run:
            verify_migration(engine)
        
        logging.info("🎉 Complete v2 migration process finished successfully")
        if backup_file:
            logging.info(f"💾 Backup saved as: {backup_file}")
        
    except Exception as e:
        logging.error(f"💥 Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 