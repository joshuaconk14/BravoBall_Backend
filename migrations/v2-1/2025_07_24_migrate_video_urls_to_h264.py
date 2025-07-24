#!/usr/bin/env python3
"""
Migration: Update Video URLs to H.264 Compatible Bucket
Date: 2025-01-24
Purpose: Update video URLs from bravoball-drills to bravoball-h264 bucket for Android compatibility

This migration updates video URLs in both:
- drills table (default drills)
- custom_drills table (user-created drills)

Run this script after converting videos to H.264 format and uploading to new S3 bucket.
"""

import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Get the directory containing this script
SCRIPT_DIR = Path(__file__).parent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(SCRIPT_DIR / f'migration_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VideoUrlMigrator:
    def __init__(self, database_url=None):
        """Initialize the migrator with database connection"""
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Migration configuration
        self.old_bucket_url = "https://bravoball-drills.s3.us-east-2.amazonaws.com"
        self.new_bucket_url = "https://bravoball-drills-h264.s3.us-east-2.amazonaws.com"
        
        logger.info(f"🔧 Initialized migrator with database: {self.database_url.split('@')[-1] if '@' in self.database_url else 'local'}")
        
    def check_migration_needed(self):
        """Check if migration is needed by looking for old bucket URLs"""
        with self.SessionLocal() as db:
            # Check drills table
            result = db.execute(text("""
                SELECT COUNT(*) as count 
                FROM drills 
                WHERE video_url LIKE '%bravoball-drills.s3.us-east-2.amazonaws.com%'
            """))
            drills_count = result.fetchone().count
            
            # Check custom_drills table
            result = db.execute(text("""
                SELECT COUNT(*) as count 
                FROM custom_drills 
                WHERE video_url LIKE '%bravoball-drills.s3.us-east-2.amazonaws.com%'
            """))
            custom_drills_count = result.fetchone().count
            
            logger.info(f"📊 Found {drills_count} drills and {custom_drills_count} custom drills with old URLs")
            return drills_count + custom_drills_count > 0
    
    def backup_current_state(self):
        """Create backup of current video URLs before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = SCRIPT_DIR / f"video_urls_backup_{timestamp}.sql"
        
        with self.SessionLocal() as db:
            # Backup drills table video URLs
            result = db.execute(text("""
                SELECT uuid, title, video_url 
                FROM drills 
                WHERE video_url IS NOT NULL
            """))
            
            with open(backup_file, 'w') as f:
                f.write("-- Video URLs Backup\n")
                f.write(f"-- Created: {datetime.now()}\n")
                f.write("-- DRILLS TABLE BACKUP\n\n")
                
                for row in result:
                    if row.video_url:
                        # Escape single quotes in SQL
                        escaped_url = row.video_url.replace("'", "''")
                        escaped_title = (row.title or "").replace("'", "''")
                        f.write(f"-- UUID: {row.uuid}, Title: {escaped_title}\n")
                        f.write(f"UPDATE drills SET video_url = '{escaped_url}' WHERE uuid = '{row.uuid}';\n\n")
            
            # Backup custom_drills table video URLs
            result = db.execute(text("""
                SELECT uuid, title, video_url 
                FROM custom_drills 
                WHERE video_url IS NOT NULL
            """))
            
            with open(backup_file, 'a') as f:
                f.write("\n-- CUSTOM DRILLS TABLE BACKUP\n\n")
                
                for row in result:
                    if row.video_url:
                        # Escape single quotes in SQL
                        escaped_url = row.video_url.replace("'", "''")
                        escaped_title = (row.title or "").replace("'", "''")
                        f.write(f"-- UUID: {row.uuid}, Title: {escaped_title}\n")
                        f.write(f"UPDATE custom_drills SET video_url = '{escaped_url}' WHERE uuid = '{row.uuid}';\n\n")
        
        logger.info(f"💾 Backup created: {backup_file}")
        return backup_file
    
    def migrate_drills_table(self):
        """Migrate video URLs in drills table"""
        logger.info("🔄 Migrating drills table...")
        
        with self.SessionLocal() as db:
            try:
                # First, get a count of what we're about to update
                count_result = db.execute(text("""
                    SELECT COUNT(*) as count 
                    FROM drills 
                    WHERE video_url LIKE '%bravoball-drills.s3.us-east-2.amazonaws.com%'
                """))
                count_before = count_result.fetchone().count
                logger.info(f"   📊 Found {count_before} drill records to update")
                
                # Update video URLs in drills table
                result = db.execute(text("""
                    UPDATE drills 
                    SET video_url = REPLACE(video_url, :old_bucket, :new_bucket)
                    WHERE video_url LIKE '%bravoball-drills.s3.us-east-2.amazonaws.com%'
                """), {
                    'old_bucket': self.old_bucket_url,
                    'new_bucket': self.new_bucket_url
                })
                
                updated_count = result.rowcount
                db.commit()
                
                logger.info(f"✅ Updated {updated_count} drill video URLs")
                return updated_count
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Error migrating drills table: {e}")
                raise
    
    def migrate_custom_drills_table(self):
        """Migrate video URLs in custom_drills table"""
        logger.info("🔄 Migrating custom_drills table...")
        
        with self.SessionLocal() as db:
            try:
                # First, get a count of what we're about to update
                count_result = db.execute(text("""
                    SELECT COUNT(*) as count 
                    FROM custom_drills 
                    WHERE video_url LIKE '%bravoball-drills.s3.us-east-2.amazonaws.com%'
                """))
                count_before = count_result.fetchone().count
                logger.info(f"   📊 Found {count_before} custom drill records to update")
                
                # Update video URLs in custom_drills table
                result = db.execute(text("""
                    UPDATE custom_drills 
                    SET video_url = REPLACE(video_url, :old_bucket, :new_bucket)
                    WHERE video_url LIKE '%bravoball-drills.s3.us-east-2.amazonaws.com%'
                """), {
                    'old_bucket': self.old_bucket_url,
                    'new_bucket': self.new_bucket_url
                })
                
                updated_count = result.rowcount
                db.commit()
                
                logger.info(f"✅ Updated {updated_count} custom drill video URLs")
                return updated_count
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Error migrating custom_drills table: {e}")
                raise
    
    def verify_migration(self):
        """Verify that migration was successful"""
        logger.info("🔍 Verifying migration...")
        
        with self.SessionLocal() as db:
            # Check for any remaining old URLs
            result = db.execute(text("""
                SELECT COUNT(*) as count 
                FROM drills 
                WHERE video_url LIKE '%bravoball-drills.s3.us-east-2.amazonaws.com%'
            """))
            remaining_drills = result.fetchone().count
            
            result = db.execute(text("""
                SELECT COUNT(*) as count 
                FROM custom_drills 
                WHERE video_url LIKE '%bravoball-drills.s3.us-east-2.amazonaws.com%'
            """))
            remaining_custom = result.fetchone().count
            
            # Check for new URLs
            result = db.execute(text("""
                SELECT COUNT(*) as count 
                FROM drills 
                WHERE video_url LIKE '%bravoball-drills-h264.s3.us-east-2.amazonaws.com%'
            """))
            new_drills = result.fetchone().count
            
            result = db.execute(text("""
                SELECT COUNT(*) as count 
                FROM custom_drills 
                WHERE video_url LIKE '%bravoball-drills-h264.s3.us-east-2.amazonaws.com%'
            """))
            new_custom = result.fetchone().count
            
            # Get total video URLs for reference
            result = db.execute(text("""
                SELECT COUNT(*) as count 
                FROM drills 
                WHERE video_url IS NOT NULL AND video_url != ''
            """))
            total_drill_videos = result.fetchone().count
            
            result = db.execute(text("""
                SELECT COUNT(*) as count 
                FROM custom_drills 
                WHERE video_url IS NOT NULL AND video_url != ''
            """))
            total_custom_videos = result.fetchone().count
            
            logger.info(f"📊 Migration Results:")
            logger.info(f"   📉 Remaining old URLs: {remaining_drills + remaining_custom}")
            logger.info(f"   📈 New H.264 URLs: {new_drills + new_custom}")
            logger.info(f"   📊 Total videos with URLs: {total_drill_videos + total_custom_videos}")
            
            # If we have remaining old URLs, show some examples for debugging
            if remaining_drills + remaining_custom > 0:
                logger.warning(f"⚠️ Found {remaining_drills + remaining_custom} URLs that still need migration")
                
                # Show examples of remaining old URLs for debugging
                result = db.execute(text("""
                    SELECT title, video_url 
                    FROM drills 
                    WHERE video_url LIKE '%bravoball-drills.s3.us-east-2.amazonaws.com%'
                    LIMIT 3
                """))
                
                remaining_examples = result.fetchall()
                if remaining_examples:
                    logger.warning("🔍 Examples of remaining old URLs:")
                    for row in remaining_examples:
                        logger.warning(f"   📄 {row.title}: {row.video_url}")
                
                return False
            
            # Check if we have the expected number of converted URLs
            if new_drills + new_custom > 0:
                logger.info("✅ Migration completed successfully!")
                logger.info(f"🎯 Successfully migrated {new_drills + new_custom} video URLs to H.264 bucket")
                return True
            else:
                logger.warning("⚠️ No H.264 URLs found after migration - this might indicate an issue")
                return False
    
    def run_migration(self, dry_run=False):
        """Run the complete migration process"""
        logger.info("🎬 Starting Video URL Migration to H.264 Bucket")
        logger.info(f"📅 Migration Date: {datetime.now()}")
        logger.info(f"🔄 Dry Run Mode: {dry_run}")
        
        # Check if migration is needed
        migration_needed = self.check_migration_needed()
        
        if not migration_needed:
            logger.info("✅ No migration needed - all URLs already updated")
            # Double-check by running verification
            if self.verify_migration():
                logger.info("🎯 Verification confirmed: Migration already completed successfully")
            return True
        
        if not dry_run:
            # Create backup before migration
            backup_file = self.backup_current_state()
            logger.info(f"💾 Backup saved to: {backup_file}")
        
        try:
            if dry_run:
                logger.info("🧪 DRY RUN - No changes will be made")
                # Show what would be changed
                with self.SessionLocal() as db:
                    result = db.execute(text("""
                        SELECT title, video_url 
                        FROM drills 
                        WHERE video_url LIKE '%bravoball-drills.s3.us-east-2.amazonaws.com%'
                        LIMIT 5
                    """))
                    
                    logger.info("📋 Sample drills that would be updated:")
                    for row in result:
                        old_url = row.video_url
                        new_url = old_url.replace(self.old_bucket_url, self.new_bucket_url)
                        logger.info(f"   📄 {row.title}")
                        logger.info(f"      🔗 {old_url}")
                        logger.info(f"      ➡️  {new_url}")
                        logger.info("")
                        
                    # Also show custom drills sample
                    result = db.execute(text("""
                        SELECT title, video_url 
                        FROM custom_drills 
                        WHERE video_url LIKE '%bravoball-drills.s3.us-east-2.amazonaws.com%'
                        LIMIT 3
                    """))
                    
                    if result.rowcount > 0:
                        logger.info("📋 Sample custom drills that would be updated:")
                        for row in result:
                            old_url = row.video_url
                            new_url = old_url.replace(self.old_bucket_url, self.new_bucket_url)
                            logger.info(f"   📄 {row.title}")
                            logger.info(f"      🔗 {old_url}")
                            logger.info(f"      ➡️  {new_url}")
                            logger.info("")
                            
                return True
            else:
                # Perform actual migration
                drills_updated = self.migrate_drills_table()
                custom_drills_updated = self.migrate_custom_drills_table()
                
                total_updated = drills_updated + custom_drills_updated
                logger.info(f"📊 Total URLs updated: {total_updated}")
                
                # Verify migration
                success = self.verify_migration()
                
                if success:
                    logger.info("🎉 Migration completed successfully!")
                    return True
                else:
                    logger.error("❌ Migration verification failed - check logs for details")
                    return False
                    
        except Exception as e:
            logger.error(f"💥 Migration failed: {e}")
            if not dry_run:
                logger.error("💡 You can restore from the backup file if needed")
            raise

def main():
    """Main entry point for migration script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate video URLs to H.264 bucket')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying them')
    parser.add_argument('--database-url', help='Database URL (overrides environment variable)')
    
    args = parser.parse_args()
    
    try:
        migrator = VideoUrlMigrator(database_url=args.database_url)
        success = migrator.run_migration(dry_run=args.dry_run)
        
        if success:
            logger.info("✅ Migration script completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Migration script failed")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"💥 Migration script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 