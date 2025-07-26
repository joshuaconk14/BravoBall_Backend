#!/usr/bin/env python3
"""
Mental Training Quotes Seeding Script
Loads quotes from mental_training_quotes.txt and seeds them into the database
"""

import json
import os
import sys
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def load_quotes_from_file():
    """Load quotes from the JSON file"""
    # Get the path to the quotes file (relative to backend root)
    quotes_file = os.path.join(os.path.dirname(__file__), '..', 'drills', 'mental_training_quotes.txt')
    
    try:
        with open(quotes_file, 'r', encoding='utf-8') as f:
            quotes = json.load(f)
        
        logging.info(f"✅ Loaded {len(quotes)} quotes from file")
        return quotes
    except FileNotFoundError:
        logging.error(f"❌ Quotes file not found: {quotes_file}")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"❌ Error parsing quotes JSON: {e}")
        return []

def seed_mental_training_quotes(engine, quotes, dry_run=False):
    """Seed mental training quotes into the database"""
    
    if not quotes:
        logging.warning("⚠️ No quotes to seed")
        return False
    
    with engine.connect() as conn:
        # Check if quotes already exist
        result = conn.execute(text("SELECT COUNT(*) FROM mental_training_quotes"))
        existing_count = result.fetchone()[0]
        
        if existing_count > 0:
            logging.info(f"📋 Found {existing_count} existing quotes in database")
            if not dry_run:
                # Clear existing quotes to avoid duplicates
                conn.execute(text("DELETE FROM mental_training_quotes"))
                conn.commit()
                logging.info("🗑️ Cleared existing quotes")
        
        if dry_run:
            logging.info(f"🔍 DRY RUN: Would insert {len(quotes)} quotes")
            for i, quote in enumerate(quotes[:3], 1):  # Show first 3 as preview
                logging.info(f"  Quote {i}: \"{quote['content'][:60]}...\" - {quote['author']}")
            if len(quotes) > 3:
                logging.info(f"  ... and {len(quotes) - 3} more quotes")
            return True
        
        # Insert quotes with proper sequence
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
                
                if i % 10 == 0:  # Log progress every 10 quotes
                    logging.info(f"📝 Inserted {i}/{len(quotes)} quotes...")
                    
            except Exception as e:
                logging.error(f"❌ Error inserting quote {i}: {e}")
                logging.error(f"Quote content: {quote['content'][:100]}...")
        
        # Update the sequence for the ID column
        try:
            conn.execute(text("SELECT setval('mental_training_quotes_id_seq', :max_id, true)"), {'max_id': len(quotes)})
            logging.info(f"🔢 Updated ID sequence to {len(quotes)}")
        except Exception as e:
            logging.warning(f"⚠️ Could not update sequence: {e}")
        
        conn.commit()
        logging.info(f"✅ Successfully seeded {success_count}/{len(quotes)} mental training quotes")
        
        return success_count == len(quotes)

def verify_seeded_quotes(engine):
    """Verify that quotes were seeded correctly"""
    with engine.connect() as conn:
        # Get total count
        result = conn.execute(text("SELECT COUNT(*) FROM mental_training_quotes"))
        total_count = result.fetchone()[0]
        
        # Get sample quotes
        result = conn.execute(text("""
            SELECT content, author, type, display_duration 
            FROM mental_training_quotes 
            ORDER BY id 
            LIMIT 3
        """))
        sample_quotes = result.fetchall()
        
        logging.info(f"🔍 Verification: {total_count} quotes in database")
        
        for i, quote in enumerate(sample_quotes, 1):
            logging.info(f"  Sample {i}: \"{quote[0][:50]}...\" - {quote[1]} ({quote[3]}s)")
        
        return total_count > 0

def main():
    """Main seeding function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed Mental Training Quotes')
    parser.add_argument('--dry-run', action='store_true', help='Preview what would be seeded')
    parser.add_argument('--database-url', help='Custom database URL')
    parser.add_argument('--force', action='store_true', help='Force re-seed even if quotes exist')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info("🌱 Starting Mental Training Quotes Seeding")
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Get database URL
        database_url = args.database_url or os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL not found in environment or arguments")
        
        # Create engine
        engine = create_engine(database_url)
        logging.info("🔗 Connected to database")
        
        # Load quotes from file
        quotes = load_quotes_from_file()
        if not quotes:
            logging.error("❌ No quotes loaded, exiting")
            sys.exit(1)
        
        # Seed quotes
        success = seed_mental_training_quotes(engine, quotes, dry_run=args.dry_run)
        
        if not args.dry_run and success:
            # Verify seeding
            verify_seeded_quotes(engine)
        
        if success:
            logging.info("🎉 Mental training quotes seeding completed successfully")
        else:
            logging.error("❌ Seeding failed")
            sys.exit(1)
        
    except Exception as e:
        logging.error(f"💥 Seeding failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 