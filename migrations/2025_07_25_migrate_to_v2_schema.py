#!/usr/bin/env python3
"""
Migration: Migrate Database Schema to v2
Date: 2025-07-25
Purpose: Apply all schema changes for BravoBall v2
"""

import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

def setup_logging():
    """Setup logging for migration"""
    log_filename = f"migration_log_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}.log"
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
    backup_filename = f"v2_schema_backup_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}.sql"
    database_url = str(engine.url)
    
    logging.info(f"Creating backup: {{backup_filename}}")
    
    # Use pg_dump to create backup
    import subprocess
    try:
        result = subprocess.run([
            'pg_dump', database_url, '--no-owner', '--no-privileges'
        ], capture_output=True, text=True, check=True)
        
        with open(backup_filename, 'w') as f:
            f.write(result.stdout)
        
        logging.info(f"✅ Backup created: {{backup_filename}}")
        return backup_filename
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Backup failed: {{e}}")
        raise

def run_migration(engine, dry_run=False):
    """Run the v2 schema migration"""
    
    migration_sql = """
-- Create new table: mental_training_quotes
CREATE TABLE IF NOT EXISTS mental_training_quotes (
    id integer NOT NULL,
    content character varying NOT NULL,
    author character varying NOT NULL,
    type character varying NOT NULL,
    display_duration integer,
    created_at timestamp without time zone DEFAULT now()
);

-- Create new table: custom_drills
CREATE TABLE IF NOT EXISTS custom_drills (
    id integer NOT NULL,
    uuid uuid NOT NULL,
    user_id integer NOT NULL,
    title character varying NOT NULL,
    description character varying NOT NULL,
    duration integer,
    intensity character varying,
    training_styles json,
    type character varying,
    sets integer,
    reps integer,
    rest integer,
    equipment json,
    suitable_locations json,
    difficulty character varying,
    instructions json,
    tips json,
    common_mistakes json,
    progression_steps json,
    variations json,
    video_url character varying,
    thumbnail_url character varying,
    primary_skill json,
    secondary_skills json,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_custom boolean DEFAULT true
);

-- Create new table: mental_training_sessions
CREATE TABLE IF NOT EXISTS mental_training_sessions (
    id integer NOT NULL,
    user_id integer,
    date timestamp without time zone DEFAULT now(),
    duration_minutes integer NOT NULL,
    session_type character varying
);

-- Create new table: drill_skill_focus_backup_1752820920
CREATE TABLE IF NOT EXISTS drill_skill_focus_backup_1752820920 (
    id integer,
    drill_id integer,
    category character varying,
    sub_skill character varying,
    is_primary boolean,
    drill_uuid uuid
);

-- Create new table: email_verification_codes
CREATE TABLE IF NOT EXISTS email_verification_codes (
    id integer NOT NULL,
    user_id integer,
    new_email character varying,
    code character varying,
    expires_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    is_used boolean DEFAULT false
);
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS dribbling_drills_completed integer DEFAULT 0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS drills_per_session double precision DEFAULT 0.0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS shooting_drills_completed integer DEFAULT 0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS fitness_drills_completed integer DEFAULT 0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS mental_training_sessions integer DEFAULT 0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS beginner_drills_completed integer DEFAULT 0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS most_improved_skill character varying DEFAULT ''::character varying;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS previous_streak integer DEFAULT 0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS defending_drills_completed integer DEFAULT 0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS first_touch_drills_completed integer DEFAULT 0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS minutes_per_session double precision DEFAULT 0.0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS total_mental_training_minutes integer DEFAULT 0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS passing_drills_completed integer DEFAULT 0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS advanced_drills_completed integer DEFAULT 0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS total_time_all_sessions integer DEFAULT 0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS intermediate_drills_completed integer DEFAULT 0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS unique_drills_completed integer DEFAULT 0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS goalkeeping_drills_completed integer DEFAULT 0;
ALTER TABLE progress_history ADD COLUMN IF NOT EXISTS favorite_drill character varying DEFAULT ''::character varying;
ALTER TABLE drills ADD COLUMN IF NOT EXISTS is_custom boolean DEFAULT false;
ALTER TABLE drills ADD COLUMN IF NOT EXISTS uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL;
ALTER TABLE drill_skill_focus ADD COLUMN IF NOT EXISTS drill_uuid uuid;
ALTER TABLE drill_group_items ADD COLUMN IF NOT EXISTS drill_uuid uuid;
ALTER TABLE completed_sessions ADD COLUMN IF NOT EXISTS session_type character varying DEFAULT 'drill_training'::character varying;
ALTER TABLE completed_sessions ADD COLUMN IF NOT EXISTS duration_minutes integer;
ALTER TABLE completed_sessions ADD COLUMN IF NOT EXISTS mental_training_session_id integer;
ALTER TABLE ordered_session_drills ADD COLUMN IF NOT EXISTS drill_uuid uuid;
-- ALTER TABLE ordered_session_drills ALTER COLUMN sets_done TYPE integer;""".strip()
    
    statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
    
    logging.info(f"Migration contains {{len(statements)}} SQL statements")
    
    if dry_run:
        logging.info("🔍 DRY RUN MODE - No changes will be applied")
        for i, stmt in enumerate(statements, 1):
            if not stmt.startswith('--'):
                logging.info(f"Would execute {{i}}: {{stmt[:100]}}...")
        return
    
    # Execute migration statements
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            for i, stmt in enumerate(statements, 1):
                if stmt.startswith('--'):
                    logging.info(f"Comment {{i}}: {{stmt}}")
                    continue
                    
                logging.info(f"Executing {{i}}: {{stmt[:100]}}...")
                conn.execute(text(stmt))
            
            trans.commit()
            logging.info("✅ Migration completed successfully")
            
        except Exception as e:
            trans.rollback()
            logging.error(f"❌ Migration failed: {{e}}")
            raise

def verify_migration(engine):
    """Verify migration was applied correctly"""
    logging.info("🔍 Verifying migration...")
    
    # Add verification queries here
    verification_queries = [
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
        "SELECT COUNT(*) FROM mental_training_quotes",
        "SELECT COUNT(*) FROM custom_drills", 
        "SELECT COUNT(*) FROM mental_training_sessions",
        "SELECT COUNT(*) FROM email_verification_codes",
    ]
    
    with engine.connect() as conn:
        for query in verification_queries:
            result = conn.execute(text(query))
            if 'COUNT' in query:
                count = result.fetchone()[0]
                table_name = query.split('FROM ')[1]
                logging.info(f"Verification: {count} records in {table_name}")
            else:
                logging.info(f"Verification: {result.rowcount} results for: {query[:50]}...")
    
    logging.info("✅ Migration verification completed")

def seed_mental_training_quotes(engine):
    """Seed mental training quotes from JSON file"""
    import json
    import os
    
    logging.info("🌱 Starting mental training quotes seeding...")
    
    try:
        # Get the path to the quotes file (relative to migrations folder)
        quotes_file = os.path.join(os.path.dirname(__file__), '..', 'drills', 'mental_training_quotes.txt')
        
        with open(quotes_file, 'r', encoding='utf-8') as f:
            quotes = json.load(f)
        
        logging.info(f"✅ Loaded {{len(quotes)}} quotes from file")
        
        with engine.connect() as conn:
            # Check if quotes already exist
            result = conn.execute(text("SELECT COUNT(*) FROM mental_training_quotes"))
            existing_count = result.fetchone()[0]
            
            if existing_count > 0:
                logging.info(f"📋 Found {{existing_count}} existing quotes, skipping seeding")
                return True
            
            # # Create sequence if it doesn't exist
            # conn.execute(text('CREATE SEQUENCE IF NOT EXISTS mental_training_quotes_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1'))
            # conn.execute(text('ALTER TABLE mental_training_quotes ALTER COLUMN id SET DEFAULT nextval(\\'mental_training_quotes_id_seq\\'::regclass)'))
            
            # Insert quotes
            insert_sql = """
            INSERT INTO mental_training_quotes (id, content, author, type, display_duration, created_at)
            VALUES (:id, :content, :author, :type, :display_duration, NOW())
            """
            
            success_count = 0
            for i, quote in enumerate(quotes, 1):
                try:
                    conn.execute(text(insert_sql), {{
                        'id': i,
                        'content': quote['content'],
                        'author': quote['author'],
                        'type': quote['type'],
                        'display_duration': quote['display_duration']
                    }})
                    success_count += 1
                    
                    if i % 10 == 0:
                        logging.info(f"📝 Seeded {{i}}/{{len(quotes)}} quotes...")
                        
                except Exception as e:
                    logging.error(f"❌ Error seeding quote {{i}}: {{e}}")
            
            # Update the sequence
            conn.execute(text("SELECT setval('mental_training_quotes_id_seq', :max_id, true)"), {{'max_id': len(quotes)}})
            
            conn.commit()
            logging.info(f"✅ Successfully seeded {{success_count}}/{{len(quotes)}} mental training quotes")
            
            return success_count == len(quotes)
            
    except Exception as e:
        logging.error(f"❌ Error seeding mental training quotes: {{e}}")
        return False

def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate to BravoBall v2 Schema')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--database-url', help='Custom database URL')
    parser.add_argument('--skip-backup', action='store_true', help='Skip backup creation')
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = setup_logging()
    logging.info("🚀 Starting BravoBall v2 schema migration")
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Get database URL
        database_url = args.database_url or os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL not found in environment or arguments")
        
        # Create engine
        engine = create_engine(database_url)
        logging.info(f"Connected to database: {{database_url.split('@')[1] if '@' in database_url else 'localhost'}}")
        
        # Create backup (unless skipped or dry run)
        backup_file = None
        if not args.dry_run and not args.skip_backup:
            backup_file = backup_database(engine)
        
        # Run migration
        run_migration(engine, dry_run=args.dry_run)
        
        # Verify migration (unless dry run)
        if not args.dry_run:
            verify_migration(engine)
            
            # ✅ NEW: Seed mental training quotes after migration
            logging.info("🌱 Seeding mental training quotes...")
            try:
                seed_success = seed_mental_training_quotes(engine)
                if seed_success:
                    logging.info("✅ Mental training quotes seeded successfully")
                else:
                    logging.warning("⚠️ Mental training quotes seeding had issues")
            except Exception as e:
                logging.error(f"❌ Error seeding quotes: {{{{e}}}}")
        
        logging.info("🎉 Migration process completed successfully")
        if backup_file:
            logging.info(f"💾 Backup saved as: {{backup_file}}")
        
    except Exception as e:
        logging.error(f"💥 Migration failed: {{e}}")
        sys.exit(1)

if __name__ == "__main__":
    main()
