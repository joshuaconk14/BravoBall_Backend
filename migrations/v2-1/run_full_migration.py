#!/usr/bin/env python3
"""
run_full_migration.py
Full migration runner for V1 to V2/Staging database migration
"""

import sys
import os
import argparse
from pathlib import Path
import logging
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from migration_config import config
from v2_migration_manager import V2MigrationManager
from models import User
from models_v1 import UserV1

# Set up logging (console only)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def validate_configuration():
    """Validate that all required configuration is present"""
    try:
        if not config.validate():
            logger.error("❌ Configuration validation failed")
            return False
        
        logger.info("✅ Configuration validated successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Configuration validation error: {e}")
        return False

def process_user_parallel(migration_manager, v1_user, staging_emails, user_index, total_users):
    """Process a single user in parallel - thread-safe version with separate database sessions"""
    try:
        email = v1_user.email
        logger.info(f"📧 [{user_index}/{total_users}] Processing: {email}")
        
        # Create a new migration manager instance for this thread (thread-safe)
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from v2_migration_manager import V2MigrationManager
        
        # Create separate database sessions for this thread
        thread_migration_manager = V2MigrationManager(
            migration_manager.v1_engine.url,
            migration_manager.v2_engine.url
        )
        
        try:
            # Check if user exists in staging
            if email.lower() in staging_emails:
                logger.info(f"   🔄 Overwriting stale data for {email}")
                success = thread_migration_manager._migrate_apple_user_overwrite(email)
                if success:
                    logger.info(f"   ✅ Successfully updated {email}")
                    return {'status': 'updated', 'email': email, 'error': None}
                else:
                    logger.error(f"   ❌ Failed to update {email}")
                    return {'status': 'failed', 'email': email, 'error': f"Failed to update {email}"}
            else:
                logger.info(f"   ➕ Creating new user {email}")
                success = thread_migration_manager._migrate_apple_user_create(email)
                if success:
                    logger.info(f"   ✅ Successfully created {email}")
                    return {'status': 'created', 'email': email, 'error': None}
                else:
                    logger.error(f"   ❌ Failed to create {email}")
                    return {'status': 'failed', 'email': email, 'error': f"Failed to create {email}"}
                    
        finally:
            # Clean up thread-specific sessions
            try:
                thread_migration_manager.v1_session.close()
                thread_migration_manager.v2_session.close()
            except:
                pass
                
    except Exception as e:
        logger.error(f"   ❌ Error processing {email}: {e}")
        return {'status': 'failed', 'email': email, 'error': f"Error processing {email}: {e}"}

def get_user_statistics(migration_manager):
    """Get statistics about users in both databases"""
    try:
        # Get V1 user count
        v1_users = migration_manager.v1_session.query(UserV1).all()
        v1_emails = {user.email.lower() for user in v1_users}
        logger.info(f"📊 V1 Database: {len(v1_users)} users")
        
        # Get staging user count
        staging_users = migration_manager.v2_session.query(User).all()
        staging_emails = {user.email.lower() for user in staging_users}
        logger.info(f"📊 Staging Database: {len(staging_users)} users")
        
        # Find Apple users (in V1 but may or may not be in staging)
        apple_users = v1_emails
        logger.info(f"🍎 Apple Users (V1): {len(apple_users)} users")
        
        # Find users in both (stale data scenario)
        users_in_both = v1_emails & staging_emails
        logger.info(f"🔄 Users in both databases (stale data): {len(users_in_both)} users")
        
        # Find new Apple users (V1 only)
        new_apple_users = v1_emails - staging_emails
        logger.info(f"➕ New Apple users (V1 only): {len(new_apple_users)} users")
        
        # Find Android users (staging only)
        android_users = staging_emails - v1_emails
        logger.info(f"🤖 Android users (staging only): {len(android_users)} users")
        
        return {
            'v1_users': len(v1_users),
            'staging_users': len(staging_users),
            'apple_users': len(apple_users),
            'users_in_both': len(users_in_both),
            'new_apple_users': len(new_apple_users),
            'android_users': len(android_users),
            'users_in_both_emails': list(users_in_both)[:10],  # First 10 for preview
            'new_apple_emails': list(new_apple_users)[:10]     # First 10 for preview
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting user statistics: {e}")
        return None

def run_migration(migration_manager, dry_run=False, limit=None, start_from=None, batch_size=25, batch_delay=30, parallel_workers=1):
    """Run the full migration with trickle/batch processing"""
    try:
        logger.info("🚀 Starting hybrid trickle migration process...")
        logger.info(f"📦 Batch size: {batch_size} users per batch")
        logger.info(f"⏱️  Batch delay: {batch_delay} seconds between batches")
        logger.info(f"🔄 Parallel workers: {parallel_workers} users processed simultaneously per batch")
        
        # Get platform information from migration manager
        platform_info = migration_manager.identify_user_platforms()
        if not platform_info:
            logger.error("❌ Failed to identify user platforms")
            return False
        
        logger.info("📋 Migration Plan:")
        logger.info(f"   • Users with stale data to overwrite: {platform_info['apple_in_both']}")
        logger.info(f"   • New Apple users to create: {platform_info['apple_only_v1']}")
        logger.info(f"   • Android users to preserve: {platform_info['android_users']}")
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be made")
            logger.info(f"   • Would overwrite stale data for: {list(platform_info['apple_emails_in_both'])[:10]}")
            logger.info(f"   • Would create new users for: {list(platform_info['apple_emails_only_v1'])[:10]}")
            return True
        
        # Confirm before proceeding
        print("\n" + "="*60)
        print("⚠️  TRICKLE MIGRATION CONFIRMATION")
        print("="*60)
        print(f"Target Database: {config.get_database_url('staging')}")
        print(f"Users to migrate: {platform_info['apple_users_total']} Apple users from V1")
        print(f"  - Overwrite stale data: {platform_info['apple_in_both']} users (exist in both V1 and staging)")
        print(f"  - Create new entries: {platform_info['apple_only_v1']} users (only in V1)")
        print(f"Android users preserved: {platform_info['android_users']} users (only in staging)")
        print(f"")
        print(f"📊 Expected Final Database State:")
        current_staging_users = platform_info['apple_in_both'] + platform_info['android_users']
        expected_final_users = current_staging_users + platform_info['apple_only_v1']
        print(f"  - Current staging users: {current_staging_users}")
        print(f"  - New users to be added: {platform_info['apple_only_v1']}")
        print(f"  - Expected final total: {expected_final_users} users")
        print(f"")
        print(f"Batch size: {batch_size} users per batch")
        print(f"Parallel workers: {parallel_workers} users simultaneously per batch")
        print(f"Batch delay: {batch_delay} seconds")
        estimated_time = (platform_info['apple_users_total'] / batch_size) * batch_delay / 60
        print(f"Estimated time: ~{estimated_time:.1f} minutes")
        if parallel_workers > 1:
            print(f"Expected speed improvement: ~{parallel_workers}x faster than sequential processing")
        else:
            print(f"Expected speed improvement: ~3-5x faster with bulk operations (sequential processing)")
        print("="*60)
        
        confirm = input("\nDo you want to proceed with the trickle migration? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y']:
            logger.info("❌ Migration cancelled by user")
            return False
        
        # Start migration
        migration_stats = {
            'users_updated': 0,
            'users_created': 0,
            'users_failed': 0,
            'batches_completed': 0,
            'errors': []
        }
        
        # Get all Apple users from V1
        v1_users = migration_manager.v1_session.query(UserV1).all()
        staging_emails = platform_info['apple_emails_in_both'] | platform_info['android_emails']
        
        total_users = len(v1_users)
        
        # Apply start_from offset
        if start_from:
            # Filter users by ID instead of array index to handle gaps in ID sequence
            v1_users = [user for user in v1_users if user.id >= start_from]
            total_users = len(v1_users)
            logger.info(f"🔢 Starting from user ID {start_from}, processing {total_users} remaining users")
        
        # Apply limit
        if limit:
            total_users = min(total_users, limit)
            v1_users = v1_users[:limit]
            logger.info(f"🔢 Limited to {limit} users")
        
        # Calculate total batches
        total_batches = (total_users + batch_size - 1) // batch_size
        logger.info(f"🔄 Processing {total_users} Apple users in {total_batches} batches...")
        
        # Process users in batches
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_users)
            batch_users = v1_users[start_idx:end_idx]
            
            # Calculate actual user numbers for display
            actual_start = (start_from - 1) if start_from else 0
            display_start = actual_start + start_idx + 1
            display_end = actual_start + end_idx
            
            logger.info(f"\n📦 BATCH {batch_num + 1}/{total_batches} - Processing users {display_start}-{display_end}")
            
            batch_stats = {
                'updated': 0,
                'created': 0,
                'failed': 0,
                'errors': []
            }
            
            # Process users in parallel within the current batch
            logger.info(f"🔄 Processing {len(batch_users)} users with {parallel_workers} parallel workers...")
            
            with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
                # Submit all users in the batch for parallel processing
                future_to_user = {
                    executor.submit(
                        process_user_parallel, 
                        migration_manager, 
                        v1_user, 
                        staging_emails, 
                        display_start + i, 
                        total_users
                    ): v1_user 
                    for i, v1_user in enumerate(batch_users)
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_user):
                    try:
                        result = future.result()
                        email = result['email']
                        
                        if result['status'] == 'updated':
                            batch_stats['updated'] += 1
                            migration_stats['users_updated'] += 1
                        elif result['status'] == 'created':
                            batch_stats['created'] += 1
                            migration_stats['users_created'] += 1
                        elif result['status'] == 'failed':
                            batch_stats['failed'] += 1
                            migration_stats['users_failed'] += 1
                            if result['error']:
                                batch_stats['errors'].append(result['error'])
                                migration_stats['errors'].append(result['error'])
                                
                    except Exception as e:
                        batch_stats['failed'] += 1
                        migration_stats['users_failed'] += 1
                        error_msg = f"Error in parallel processing: {e}"
                        batch_stats['errors'].append(error_msg)
                        migration_stats['errors'].append(error_msg)
                        logger.error(f"   ❌ Error in parallel processing: {e}")
            
            # Batch completion summary
            migration_stats['batches_completed'] += 1
            logger.info(f"\n📊 BATCH {batch_num + 1} COMPLETED:")
            logger.info(f"   ✅ Updated: {batch_stats['updated']}")
            logger.info(f"   ✅ Created: {batch_stats['created']}")
            logger.info(f"   ❌ Failed: {batch_stats['failed']}")
            logger.info(f"   📈 Success rate: {(batch_stats['updated'] + batch_stats['created']) / len(batch_users) * 100:.1f}%")
            
            # Add delay between batches (except for the last batch)
            if batch_num < total_batches - 1:
                logger.info(f"⏸️  Waiting {batch_delay} seconds before next batch...")
                import time
                time.sleep(batch_delay)
        
        # Final statistics
        logger.info("\n" + "="*60)
        logger.info("🎉 TRICKLE MIGRATION COMPLETED")
        logger.info("="*60)
        logger.info(f"📦 Batches completed: {migration_stats['batches_completed']}/{total_batches}")
        logger.info(f"✅ Users updated (stale data): {migration_stats['users_updated']}")
        logger.info(f"✅ Users created (new): {migration_stats['users_created']}")
        logger.info(f"❌ Users failed: {migration_stats['users_failed']}")
        logger.info(f"📊 Total processed: {migration_stats['users_updated'] + migration_stats['users_created'] + migration_stats['users_failed']}")
        
        if migration_stats['errors']:
            logger.info(f"\n⚠️  Errors encountered ({len(migration_stats['errors'])}):")
            for error in migration_stats['errors'][:5]:  # Show first 5 errors
                logger.info(f"   • {error}")
            if len(migration_stats['errors']) > 5:
                logger.info(f"   • ... and {len(migration_stats['errors']) - 5} more errors")
        
        success_rate = (migration_stats['users_updated'] + migration_stats['users_created']) / total_users * 100
        logger.info(f"📈 Overall success rate: {success_rate:.1f}%")
        
        # Migration comparison with initial expectations
        logger.info(f"\n📊 MIGRATION RESULTS vs EXPECTATIONS:")
        logger.info(f"   Expected to update (stale data): {platform_info['apple_in_both']} users")
        logger.info(f"   Actually updated: {migration_stats['users_updated']} users")
        logger.info(f"   Expected to create (new users): {platform_info['apple_only_v1']} users")
        logger.info(f"   Actually created: {migration_stats['users_created']} users")
        logger.info(f"   Expected final total: {platform_info['apple_in_both'] + platform_info['android_users'] + platform_info['apple_only_v1']} users")
        logger.info(f"   Android users preserved: {platform_info['android_users']} users")
        
        # Performance metrics
        total_time = migration_stats['batches_completed'] * batch_delay
        logger.info(f"⏱️  Total time: ~{total_time / 60:.1f} minutes")
        logger.info(f"🚀 Average speed: ~{total_users / (total_time / 60):.1f} users/minute")
        logger.info(f"🔄 Parallel processing: {parallel_workers} workers per batch")
        logger.info(f"⚡ Effective speed: ~{total_users / (total_time / 60) * parallel_workers:.1f} users/minute (with parallel processing)")
        
        return migration_stats['users_failed'] == 0
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Run V1 to V2/Staging migration with trickle/batch processing')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without making changes')
    parser.add_argument('--limit', type=int, help='Limit number of users to migrate (for testing)')
    parser.add_argument('--stats-only', action='store_true', help='Show statistics only, no migration')
    parser.add_argument('--batch-size', type=int, default=25, help='Number of users to process per batch (default: 25)')
    parser.add_argument('--batch-delay', type=int, default=30, help='Seconds to wait between batches (default: 30)')
    parser.add_argument('--parallel-workers', type=int, default=1, help='Number of parallel workers per batch (default: 1 - sequential with bulk operations)')
    parser.add_argument('--start-from', type=int, help='Start migration from user number X (1-based index)')
    
    args = parser.parse_args()
    
    try:
        logger.info("🚀 V2 Migration Runner Starting...")
        logger.info(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Validate configuration
        if not validate_configuration():
            sys.exit(1)
        
        # Create migration manager
        migration_manager = V2MigrationManager(
            config.get_database_url("v1"),
            config.get_database_url("staging")  # Use staging for testing
        )
        
        if args.stats_only:
            logger.info("📊 Statistics only mode")
            platform_info = migration_manager.identify_user_platforms()
            if platform_info:
                logger.info("✅ Statistics retrieved successfully")
            sys.exit(0)
        
        # Run migration
        success = run_migration(
            migration_manager, 
            dry_run=args.dry_run, 
            limit=args.limit,
            start_from=args.start_from,
            batch_size=args.batch_size,
            batch_delay=args.batch_delay,
            parallel_workers=args.parallel_workers
        )
        
        if success:
            logger.info("🎉 Migration completed successfully!")
            sys.exit(0)
        else:
            logger.error("💥 Migration failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n⏹️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Clean up sessions
        try:
            migration_manager.v1_session.close()
            migration_manager.v2_session.close()
        except:
            pass

if __name__ == "__main__":
    main()
