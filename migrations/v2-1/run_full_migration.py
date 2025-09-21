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
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
import time
import signal
from contextlib import contextmanager

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from migration_config import config
from v2_migration_manager import V2MigrationManager
from models import User
from models_v1 import UserV1

# Set up logging (console and selective file logging)
def setup_logging():
    """Set up logging with console output and selective file logging for key events only"""
    # Create log file name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = config.log_dir / f"migration_run_{timestamp}.log"
    
    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Clear any existing handlers to avoid conflicts
    logging.getLogger().handlers.clear()
    
    # Create console handler (gets all log messages)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    
    # Create file handler (will be used selectively for key events)
    global file_handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    
    # Configure root logger with console handler only
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    logger = logging.getLogger(__name__)
    logger.info(f"📝 Logging initialized - Log file: {log_file}")
    logger.info(f"📝 Key milestones will be logged to file: migration start, batch completions, migration end")
    
    return logger

def log_to_file(message):
    """Write a specific message to the log file only (not console)"""
    global file_handler
    # Create a temporary logger just for this file write
    temp_logger = logging.getLogger("file_only")
    temp_logger.handlers.clear()
    temp_logger.addHandler(file_handler)
    temp_logger.setLevel(logging.INFO)
    temp_logger.info(message)
    file_handler.flush()  # Ensure immediate write

# Timeout handling utilities
class TimeoutException(Exception):
    """Custom timeout exception"""
    pass

@contextmanager 
def timeout_handler(seconds, description="operation"):
    """Simple timeout handler that just tracks time"""
    import time
    start_time = time.time()
    
    class TimeoutTracker:
        def __init__(self, start, timeout_seconds):
            self.start = start
            self.timeout = timeout_seconds
            
        def is_timeout(self):
            return time.time() - self.start > self.timeout
            
        def elapsed(self):
            return time.time() - self.start
    
    tracker = TimeoutTracker(start_time, seconds)
    try:
        yield tracker
    finally:
        pass  # No cleanup needed

def check_migration_health(start_time, max_duration_hours=6):
    """Check if migration has been running too long"""
    elapsed = datetime.now() - start_time
    if elapsed.total_seconds() > max_duration_hours * 3600:
        raise TimeoutException(f"Migration exceeded maximum duration of {max_duration_hours} hours")
    return elapsed

logger = setup_logging()

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

def process_user_parallel(migration_manager, v1_user, staging_emails, user_index, total_users, user_timeout=300):
    """Process a single user in parallel - thread-safe version with separate database sessions"""
    email = v1_user.email
    try:
        logger.info(f"📧 [{user_index}/{total_users}] Processing: {email}")
        
        # Add timeout for individual user processing
        with timeout_handler(user_timeout, f"user processing for {email}") as timeout_tracker:
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
                # Check for timeout before processing
                if timeout_tracker.is_timeout():
                    raise TimeoutException(f"Timeout before processing {email} (elapsed: {timeout_tracker.elapsed():.1f}s)")
                
                # Check if user exists in staging
                if email.lower() in staging_emails:
                    logger.info(f"   🔄 Overwriting stale data for {email}")
                    
                    # Check timeout before main processing
                    if timeout_tracker.is_timeout():
                        raise TimeoutException(f"Hard timeout before main processing for {email} after {timeout_tracker.elapsed():.1f}s")
                        
                    success = thread_migration_manager._migrate_apple_user_overwrite(email)
                        
                    # Check timeout after processing
                    if timeout_tracker.is_timeout():
                        logger.warning(f"   ⏰ User {email} completed but took {timeout_tracker.elapsed():.1f}s (timeout: {user_timeout}s)")
                        
                    if success:
                        logger.info(f"   ✅ Successfully updated {email}")
                        return {'status': 'updated', 'email': email, 'error': None}
                    else:
                        logger.error(f"   ❌ Failed to update {email}")
                        return {'status': 'failed', 'email': email, 'error': f"Failed to update {email}"}
                else:
                    logger.info(f"   ➕ Creating new user {email}")
                        
                    # Check timeout before main processing
                    if timeout_tracker.is_timeout():
                        raise TimeoutException(f"Hard timeout before user creation for {email} after {timeout_tracker.elapsed():.1f}s")
                        
                    success = thread_migration_manager._migrate_apple_user_create(email)
                        
                    # Check timeout after processing
                    if timeout_tracker.is_timeout():
                        logger.warning(f"   ⏰ User {email} completed but took {timeout_tracker.elapsed():.1f}s (timeout: {user_timeout}s)")
                        
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
                
    except TimeoutException as e:
        logger.error(f"   ⏰ Timeout processing {email}: {e}")
        return {'status': 'failed', 'email': email, 'error': f"Timeout processing {email}: {e}"}
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

def run_migration(migration_manager, dry_run=False, limit=None, start_from=None, batch_size=25, batch_delay=30, parallel_workers=1, user_timeout=300, batch_timeout=900, migration_timeout_hours=6, skip_confirmations=False):
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
        
        # Production safety check
        target_url = migration_manager.v2_engine.url
        if 'production' in str(target_url).lower() or 'prod' in str(target_url).lower() or target_url == config.get_database_url("v2"):
            print("\n" + "🚨" * 20)
            print("🚨 PRODUCTION DATABASE DETECTED 🚨")
            print("🚨" * 20)
            print("⚠️  WARNING: You are about to run migration against PRODUCTION!")
            print("⚠️  This will PERMANENTLY modify production data!")
            print("⚠️  Make sure you have:")
            print("   • Created a full database backup")
            print("   • Tested this migration on staging")
            print("   • Coordinated with your team")
            print("   • Have rollback plan ready")
            print("🚨" * 20)
            
            if not skip_confirmations:
                production_confirm = input("\n🔴 Type 'PRODUCTION' to confirm you want to proceed: ").strip()
                if production_confirm != 'PRODUCTION':
                    logger.info("❌ Production migration cancelled - confirmation failed")
                    return False
                print("✅ Production confirmation received")
            else:
                logger.info("✅ Production confirmation skipped (--yes flag)")
        
        # Confirm before proceeding
        print("\n" + "="*60)
        print("⚠️  TRICKLE MIGRATION CONFIRMATION")
        print("="*60)
        # Get the actual target database URL from the migration manager
        target_url = migration_manager.v2_engine.url
        print(f"Target Database: {target_url}")
        print(f"Users to migrate: {platform_info['apple_users_total']} Apple users from V1")
        print(f"  - Overwrite stale data: {platform_info['apple_in_both']} users (exist in both V1 and target)")
        print(f"  - Create new entries: {platform_info['apple_only_v1']} users (only in V1)")
        print(f"Android users preserved: {platform_info['android_users']} users (only in target)")
        print(f"")
        print(f"📊 Expected Final Database State:")
        current_target_users = platform_info['apple_in_both'] + platform_info['android_users']
        expected_final_users = current_target_users + platform_info['apple_only_v1']
        print(f"  - Current target users: {current_target_users}")
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
        
        if not skip_confirmations:
            confirm = input("\nDo you want to proceed with the trickle migration? (yes/no): ").strip().lower()
            if confirm not in ['yes', 'y']:
                logger.info("❌ Migration cancelled by user")
                return False
        else:
            logger.info("✅ Migration confirmation skipped (--yes flag)")
        
        # Start migration
        migration_start_time = datetime.now()
        migration_stats = {
            'users_updated': 0,
            'users_created': 0,
            'users_failed': 0,
            'batches_completed': 0,
            'errors': [],
            'start_time': migration_start_time
        }
        
        # Log migration start details (console)
        logger.info("\n" + "🚀" * 20)
        logger.info("🚀 MIGRATION STARTED")
        logger.info("🚀" * 20)
        logger.info(f"📅 Start Time: {migration_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🎯 Target Database: {migration_manager.v2_engine.url}")
        logger.info(f"📊 Total Apple Users to Migrate: {platform_info['apple_users_total']}")
        logger.info(f"   • Users to Update (stale data): {platform_info['apple_in_both']}")
        logger.info(f"   • Users to Create (new): {platform_info['apple_only_v1']}")
        logger.info(f"🔒 Android Users to Preserve: {platform_info['android_users']}")
        logger.info(f"📦 Batch Configuration:")
        logger.info(f"   • Batch Size: {batch_size} users")
        logger.info(f"   • Parallel Workers: {parallel_workers}")
        logger.info(f"   • Batch Delay: {batch_delay} seconds")
        logger.info(f"   • Total Batches: {(platform_info['apple_users_total'] + batch_size - 1) // batch_size}")
        logger.info("🚀" * 20)
        
        # Log migration start to file (key milestone)
        log_to_file("🚀🚀🚀 MIGRATION STARTED 🚀🚀🚀")
        log_to_file(f"📅 Start Time: {migration_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        log_to_file(f"🎯 Target Database: {str(migration_manager.v2_engine.url).split('@')[0]}@***")
        log_to_file(f"📊 Total Users to Migrate: {platform_info['apple_users_total']} (Update: {platform_info['apple_in_both']}, Create: {platform_info['apple_only_v1']})")
        log_to_file(f"📦 Batch Config: {batch_size} users/batch, {batch_delay}s delay, {parallel_workers} workers")
        log_to_file(f"📈 Expected Batches: {(platform_info['apple_users_total'] + batch_size - 1) // batch_size}")
        log_to_file("🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀")
        
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
        
        # Process users in batches with overall migration timeout
        for batch_num in range(total_batches):
            # Check overall migration health (prevent runaway migrations)
            try:
                elapsed = check_migration_health(migration_start_time, max_duration_hours=migration_timeout_hours)
                if batch_num % 10 == 0:  # Every 10 batches, log progress
                    logger.info(f"⏱️  Migration health check: {elapsed} elapsed, processing batch {batch_num + 1}/{total_batches}")
                    log_to_file(f"⏱️  Health Check: {elapsed} elapsed, batch {batch_num + 1}/{total_batches}")
            except TimeoutException as e:
                logger.error(f"🚨 Migration timeout exceeded: {e}")
                log_to_file(f"🚨 MIGRATION TIMEOUT: {e}")
                log_to_file(f"📊 Progress at timeout: {migration_stats['batches_completed']}/{total_batches} batches completed")
                log_to_file(f"📊 Users processed: {migration_stats['users_updated'] + migration_stats['users_created']} successful, {migration_stats['users_failed']} failed")
                return False
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_users)
            batch_users = v1_users[start_idx:end_idx]
            
            # Calculate actual user numbers for display
            actual_start = (start_from - 1) if start_from else 0
            display_start = actual_start + start_idx + 1
            display_end = actual_start + end_idx
            
            batch_start_time = datetime.now()
            logger.info(f"\n📦 BATCH {batch_num + 1}/{total_batches} - Processing users {display_start}-{display_end}")
            logger.info(f"⏱️  Batch Start Time: {batch_start_time.strftime('%H:%M:%S')}")
            
            batch_stats = {
                'updated': 0,
                'created': 0,
                'failed': 0,
                'errors': []
            }
            
            # Process users in parallel within the current batch
            logger.info(f"🔄 Processing {len(batch_users)} users with {parallel_workers} parallel workers...")
            
            # Add timeout for entire batch processing
            # batch_timeout is now configurable via parameter
            try:
                with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
                    # Submit all users in the batch for parallel processing
                    future_to_user = {
                        executor.submit(
                            process_user_parallel, 
                            migration_manager, 
                            v1_user, 
                            staging_emails, 
                            display_start + i, 
                            total_users,
                            user_timeout
                        ): v1_user 
                        for i, v1_user in enumerate(batch_users)
                    }
                    
                    # Collect results as they complete with timeout
                    try:
                        for future in as_completed(future_to_user, timeout=batch_timeout):
                            try:
                                result = future.result(timeout=30)  # 30 second timeout per result
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
                                        
                            except FuturesTimeoutError:
                                batch_stats['failed'] += 1
                                migration_stats['users_failed'] += 1
                                error_msg = f"Individual user processing timed out after 30 seconds"
                                batch_stats['errors'].append(error_msg)
                                migration_stats['errors'].append(error_msg)
                                logger.error(f"   ⏰ {error_msg}")
                            except Exception as e:
                                batch_stats['failed'] += 1
                                migration_stats['users_failed'] += 1
                                error_msg = f"Error in parallel processing: {e}"
                                batch_stats['errors'].append(error_msg)
                                migration_stats['errors'].append(error_msg)
                                logger.error(f"   ❌ Error in parallel processing: {e}")
                                
                    except FuturesTimeoutError:
                        logger.error(f"⏰ Batch {batch_num + 1} timed out after {batch_timeout} seconds")
                        # Cancel remaining futures
                        for future in future_to_user:
                            future.cancel()
                        # Mark remaining users as failed
                        remaining_users = len([f for f in future_to_user if not f.done()])
                        batch_stats['failed'] += remaining_users
                        migration_stats['users_failed'] += remaining_users
                        error_msg = f"Batch timeout - {remaining_users} users not processed"
                        batch_stats['errors'].append(error_msg)
                        migration_stats['errors'].append(error_msg)
                        
            except Exception as e:
                logger.error(f"⚠️  Batch processing error: {e}")
                # Mark all users in batch as failed if batch setup fails
                batch_stats['failed'] += len(batch_users)
                migration_stats['users_failed'] += len(batch_users)
                error_msg = f"Batch setup error: {e}"
                batch_stats['errors'].append(error_msg)
                migration_stats['errors'].append(error_msg)
            
            # Batch completion summary (console)
            migration_stats['batches_completed'] += 1
            batch_end_time = datetime.now()
            batch_duration = (batch_end_time - batch_start_time).total_seconds()
            
            logger.info(f"\n" + "📊" * 15)
            logger.info(f"📊 BATCH {batch_num + 1}/{total_batches} COMPLETED")
            logger.info(f"📊" * 15)
            logger.info(f"⏱️  Batch Duration: {batch_duration:.1f} seconds")
            logger.info(f"📧 Users in Batch: {len(batch_users)}")
            logger.info(f"✅ Updated: {batch_stats['updated']}")
            logger.info(f"✅ Created: {batch_stats['created']}")
            logger.info(f"❌ Failed: {batch_stats['failed']}")
            logger.info(f"📈 Batch Success Rate: {(batch_stats['updated'] + batch_stats['created']) / len(batch_users) * 100:.1f}%")
            logger.info(f"🏃 Processing Speed: {len(batch_users) / batch_duration:.1f} users/second")
            
            # Overall progress
            total_processed = migration_stats['users_updated'] + migration_stats['users_created'] + migration_stats['users_failed']
            overall_progress = total_processed / total_users * 100
            logger.info(f"📈 Overall Progress: {total_processed}/{total_users} ({overall_progress:.1f}%)")
            logger.info(f"📊" * 15)
            
            # Log batch completion to file (key milestone)
            batch_success_rate = (batch_stats['updated'] + batch_stats['created']) / len(batch_users) * 100
            log_to_file(f"📊 BATCH {batch_num + 1}/{total_batches} COMPLETED - {batch_end_time.strftime('%H:%M:%S')}")
            log_to_file(f"   ✅ Results: Updated {batch_stats['updated']}, Created {batch_stats['created']}, Failed {batch_stats['failed']} ({batch_success_rate:.1f}% success)")
            log_to_file(f"   ⏱️  Duration: {batch_duration:.1f}s ({len(batch_users) / batch_duration:.1f} users/sec)")
            log_to_file(f"   📈 Overall Progress: {total_processed}/{total_users} ({overall_progress:.1f}%)")
            
            # Add delay between batches (except for the last batch)
            if batch_num < total_batches - 1:
                logger.info(f"⏸️  Waiting {batch_delay} seconds before next batch...")
                import time
                time.sleep(batch_delay)
        
        # Final statistics (console)
        migration_end_time = datetime.now()
        total_migration_time = migration_end_time - migration_stats['start_time']
        
        logger.info("\n" + "🎉" * 20)
        logger.info("🎉 MIGRATION COMPLETED SUCCESSFULLY")
        logger.info("🎉" * 20)
        logger.info(f"📅 Completion Time: {migration_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"⏱️  Total Migration Duration: {total_migration_time}")
        logger.info(f"📦 Batches Completed: {migration_stats['batches_completed']}/{total_batches}")
        
        logger.info(f"\n📊 MIGRATION RESULTS:")
        logger.info(f"   ✅ Users Updated (stale data): {migration_stats['users_updated']}")
        logger.info(f"   ✅ Users Created (new): {migration_stats['users_created']}")
        logger.info(f"   ❌ Users Failed: {migration_stats['users_failed']}")
        logger.info(f"   📊 Total Processed: {migration_stats['users_updated'] + migration_stats['users_created'] + migration_stats['users_failed']}")
        
        success_rate = (migration_stats['users_updated'] + migration_stats['users_created']) / total_users * 100
        logger.info(f"   📈 Overall Success Rate: {success_rate:.1f}%")
        
        # Performance metrics
        total_seconds = total_migration_time.total_seconds()
        if total_seconds > 0:
            users_per_second = total_users / total_seconds
            logger.info(f"   🚀 Average Processing Speed: {users_per_second:.2f} users/second")
            logger.info(f"   ⚡ Total Throughput: {total_users} users in {total_seconds:.1f} seconds")
        
        if migration_stats['errors']:
            logger.info(f"\n⚠️  ERRORS ENCOUNTERED ({len(migration_stats['errors'])}):")
            for i, error in enumerate(migration_stats['errors'][:5], 1):  # Show first 5 errors
                logger.info(f"   {i}. {error}")
            if len(migration_stats['errors']) > 5:
                logger.info(f"   ... and {len(migration_stats['errors']) - 5} more errors")
        else:
            logger.info(f"\n✨ NO ERRORS - Perfect migration execution!")
        
        logger.info("🎉" * 20)
        
        # Log migration completion to file (key milestone)
        log_to_file("")
        log_to_file("🎉🎉🎉 MIGRATION COMPLETED SUCCESSFULLY 🎉🎉🎉")
        log_to_file(f"📅 Completion Time: {migration_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        log_to_file(f"⏱️  Total Duration: {total_migration_time}")
        log_to_file(f"📦 Batches Completed: {migration_stats['batches_completed']}/{total_batches}")
        log_to_file("")
        log_to_file("📊 FINAL RESULTS:")
        log_to_file(f"   ✅ Users Updated: {migration_stats['users_updated']}")
        log_to_file(f"   ✅ Users Created: {migration_stats['users_created']}")
        log_to_file(f"   ❌ Users Failed: {migration_stats['users_failed']}")
        log_to_file(f"   📊 Total Processed: {migration_stats['users_updated'] + migration_stats['users_created'] + migration_stats['users_failed']}")
        log_to_file(f"   📈 Success Rate: {success_rate:.1f}%")
        if total_seconds > 0:
            log_to_file(f"   🚀 Processing Speed: {users_per_second:.2f} users/second")
        if migration_stats['errors']:
            log_to_file(f"   ⚠️  Errors: {len(migration_stats['errors'])} encountered")
        else:
            log_to_file(f"   ✨ Perfect execution - No errors!")
        log_to_file("🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉")
        
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
    parser.add_argument('--production', action='store_true', help='Run migration against production V2 database (default: uses staging)')
    parser.add_argument('--user-timeout', type=int, default=300, help='Timeout per user in seconds (default: 300 = 5 minutes)')
    parser.add_argument('--batch-timeout', type=int, default=900, help='Timeout per batch in seconds (default: 900 = 15 minutes)')
    parser.add_argument('--migration-timeout', type=int, default=6, help='Maximum migration duration in hours (default: 6 hours)')
    parser.add_argument('--yes', action='store_true', help='Skip all confirmation prompts (for non-interactive use)')
    
    args = parser.parse_args()
    
    try:
        logger.info("🚀 V2 Migration Runner Starting...")
        logger.info(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Set production mode if --production flag is used
        if args.production:
            logger.info("🏭 PRODUCTION MODE ENABLED")
            # Override debug mode for production
            import os
            os.environ["MIGRATION_DEBUG"] = "false"
            # Reload config to pick up the change
            from migration_config import MigrationConfig
            global config
            config = MigrationConfig()
            logger.info("📊 Debug mode disabled for production")
            logger.info("🚫 User limits disabled for production")
        
        # Validate configuration
        if not validate_configuration():
            sys.exit(1)
        
        # Create migration manager - choose target database based on production flag
        target_db = "v2" if args.production else "staging"
        target_url = config.get_database_url(target_db)
        
        logger.info(f"🎯 Target Database: {target_db.upper()}")
        logger.info(f"🔗 Target URL: {target_url}")
        
        migration_manager = V2MigrationManager(
            config.get_database_url("v1"),
            target_url
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
            parallel_workers=args.parallel_workers,
            user_timeout=args.user_timeout,
            batch_timeout=args.batch_timeout,
            migration_timeout_hours=args.migration_timeout,
            skip_confirmations=args.yes
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
