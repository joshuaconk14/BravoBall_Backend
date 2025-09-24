"""
v2_migration_manager.py
Core migration logic that intelligently merges data based on user platforms
"""

import sys
import os
import json
from pathlib import Path
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime, date
from typing import Dict, List, Set, Optional, Tuple

# Add parent directory to path to import our models
sys.path.append(str(Path(__file__).parent.parent.parent))
from models import (
    User, CompletedSession, SessionPreferences, DrillGroup, DrillGroupItem,
    ProgressHistory, SavedFilter, RefreshToken, PasswordResetCode, EmailVerificationCode,
    MentalTrainingSession, MentalTrainingQuote, OrderedSessionDrill, TrainingSession
)
# Import V1-specific models
from models_v1 import (
    UserV1, CompletedSessionV1, SessionPreferencesV1, DrillGroupV1, DrillGroupItemV1,
    ProgressHistoryV1, SavedFilterV1, RefreshTokenV1, PasswordResetCodeV1,
    OrderedSessionDrillV1, TrainingSessionV1
)
from migration_config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(config.get_log_path("migration_manager")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class V2MigrationManager:
    """Handles intelligent migration of Apple users from V1 to V2 while preserving Android data"""
    
    def __init__(self, v1_url: str, v2_url: str):
        self.v1_engine = create_engine(v1_url)
        self.v2_engine = create_engine(v2_url)
        self.v1_session = sessionmaker(bind=self.v1_engine)()
        self.v2_session = sessionmaker(bind=self.v2_engine)()
        
        # Migration statistics
        self.stats = {
            'apple_users_updated': 0,
            'apple_users_created': 0,
            'android_users_preserved': 0,
            'related_data_migrated': 0,
            'errors': []
        }
        
        # Backup data
        self.android_backup = {}
    
    def _create_fresh_v2_session(self):
        """Create a fresh V2 session to handle rollback issues"""
        try:
            if self.v2_session:
                self.v2_session.close()
        except Exception as e:
            logger.warning(f"Error closing V2 session: {e}")
        
        self.v2_session = sessionmaker(bind=self.v2_engine)()
        logger.info("Created fresh V2 session")
        
    def identify_user_platforms(self) -> Dict[str, Set[str]]:
        """Identify Apple vs Android users based on email presence - full analysis"""
        try:
            logger.info("Identifying user platforms (full analysis)...")
            
            # Get ALL users from V1 database
            v1_users = self.v1_session.query(UserV1).all()
            v1_emails = set()
            for user in v1_users:
                if user.email:
                    v1_emails.add(user.email.lower())
            
            logger.info(f"📊 V1 Database: {len(v1_users)} total users")
            logger.info(f"📧 V1 Emails: {len(v1_emails)} valid email addresses")
            
            # Get all emails from staging to check which ones exist
            staging_users = self.v2_session.query(User).all()
            staging_emails = set()
            for user in staging_users:
                if user.email:
                    staging_emails.add(user.email.lower())
            
            logger.info(f"📊 Staging Database: {len(staging_users)} total users")
            logger.info(f"📧 Staging Emails: {len(staging_emails)} valid email addresses")
            
            # Categorize users properly
            apple_users = v1_emails  # All V1 users are Apple users (the ones we want to migrate)
            users_in_both = v1_emails & staging_emails  # Users that exist in both (stale data to update)
            apple_only_v1 = v1_emails - staging_emails  # Users only in V1 (new users to create)
            android_users = staging_emails - v1_emails  # Users only in staging (Android users to preserve)
            
            platform_info = {
                'apple_users_total': len(apple_users),
                'apple_in_both': len(users_in_both),
                'apple_only_v1': len(apple_only_v1),
                'android_users': len(android_users),
                'apple_emails_in_both': users_in_both,
                'apple_emails_only_v1': apple_only_v1,
                'android_emails': android_users
            }
            
            logger.info(f"📋 Platform identification complete:")
            logger.info(f"  🍎 Apple users (V1) to migrate: {len(apple_users)}")
            logger.info(f"  🔄 Users in both databases (stale data to update): {len(users_in_both)}")
            logger.info(f"  ➕ Users only in V1 (new users to create): {len(apple_only_v1)}")
            logger.info(f"  🤖 Android users (staging only, to preserve): {len(android_users)}")
            
            return platform_info
            
        except Exception as e:
            logger.error(f"Error identifying user platforms: {e}")
            self.stats['errors'].append(f"Platform identification failed: {e}")
            return {}
    
    def backup_android_users(self) -> bool:
        """Backup Android user data before migration"""
        try:
            logger.info("Backing up Android user data...")
            
            platform_info = self.identify_user_platforms()
            android_emails = platform_info.get('android_emails', set())
            
            if not android_emails:
                logger.info("No Android users found to backup")
                return True
            
            # Limit Android users in debug mode for testing simplicity
            backup_limit = config.get_android_backup_limit()
            if backup_limit and len(android_emails) > backup_limit:
                logger.info(f"Debug mode: Limiting Android backup to first {backup_limit} users")
                android_emails = list(android_emails)[:backup_limit]
            
            # Backup Android users and their related data
            for email in android_emails:
                try:
                    user = self.v2_session.query(User).filter(User.email == email).first()
                    if user:
                        user_data = self._get_user_data(user)
                        self.android_backup[email] = user_data
                        logger.info(f"Backed up Android user: {email}")
                except Exception as e:
                    logger.error(f"Error backing up Android user {email}: {e}")
                    self.stats['errors'].append(f"Android backup failed for {email}: {e}")
            
            # Save backup to file
            backup_path = config.get_backup_path("android_users_backup")
            with open(backup_path, 'w') as f:
                json.dump(self.android_backup, f, indent=2, default=str)
            
            logger.info(f"✅ Android user backup completed: {len(self.android_backup)} users")
            return True
            
        except Exception as e:
            logger.error(f"Error backing up Android users: {e}")
            self.stats['errors'].append(f"Android backup failed: {e}")
            return False
    
    def _get_user_data(self, user: User) -> dict:
        """Get all data related to a user"""
        try:
            user_data = {
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'hashed_password': user.hashed_password,
                    'primary_goal': user.primary_goal,
                    'biggest_challenge': user.biggest_challenge,
                    'training_experience': user.training_experience,
                    'position': user.position,
                    'playstyle': user.playstyle,
                    'age_range': user.age_range,
                    'strengths': user.strengths,
                    'areas_to_improve': user.areas_to_improve,
                    'training_location': user.training_location,
                    'available_equipment': user.available_equipment,
                    'daily_training_time': user.daily_training_time,
                    'weekly_training_days': user.weekly_training_days
                },
                'completed_sessions': [],
                'session_preferences': None,
                'drill_groups': [],
                'progress_history': None,
                'refresh_tokens': [],
                'password_reset_codes': [],
                # Note: V1 doesn't have email_verification_codes table
                'mental_training_sessions': []
            }
            
            # Get related data using explicit queries instead of relationships
            # Get completed sessions
            completed_sessions = self.v2_session.query(CompletedSession).filter(CompletedSession.user_id == user.id).all()
            user_data['completed_sessions'] = [
                {
                    'id': session.id,
                    'date': session.date.isoformat() if session.date else None,
                    'session_type': session.session_type,
                    'total_completed_drills': session.total_completed_drills,
                    'total_drills': session.total_drills,
                    'drills': session.drills,
                    'duration_minutes': session.duration_minutes,
                    'mental_training_session_id': session.mental_training_session_id
                }
                for session in completed_sessions
            ]
            
            # Get session preferences
            session_prefs = self.v2_session.query(SessionPreferences).filter(SessionPreferences.user_id == user.id).first()
            if session_prefs:
                user_data['session_preferences'] = {
                    'id': session_prefs.id,
                    'duration': session_prefs.duration,
                    'available_equipment': session_prefs.available_equipment,
                    'training_style': session_prefs.training_style,
                    'training_location': session_prefs.training_location,
                    'difficulty': session_prefs.difficulty,
                    'target_skills': session_prefs.target_skills,
                    'created_at': session_prefs.created_at.isoformat() if session_prefs.created_at else None,
                    'updated_at': session_prefs.updated_at.isoformat() if session_prefs.updated_at else None
                }
            
            # Get drill groups
            drill_groups = self.v2_session.query(DrillGroup).filter(DrillGroup.user_id == user.id).all()
            for group in drill_groups:
                group_data = {
                    'id': group.id,
                    'name': group.name,
                    'description': group.description,
                    'is_liked_group': group.is_liked_group,
                    'drill_items': []
                }
                
                # Get drill group items
                drill_items = self.v2_session.query(DrillGroupItem).filter(DrillGroupItem.drill_group_id == group.id).all()
                for item in drill_items:
                    group_data['drill_items'].append({
                        'id': item.id,
                        'drill_uuid': str(item.drill_uuid),
                        'is_custom': getattr(item, 'is_custom', None),
                        'added_at': getattr(item, 'added_at', None).isoformat() if getattr(item, 'added_at', None) else None
                    })
                
                user_data['drill_groups'].append(group_data)
            
            # Get progress history
            progress = self.v2_session.query(ProgressHistory).filter(ProgressHistory.user_id == user.id).first()
            if progress:
                user_data['progress_history'] = {
                    'id': progress.id,
                    'total_sessions': getattr(progress, 'total_sessions', getattr(progress, 'completed_sessions_count', 0)),
                    'total_drills_completed': getattr(progress, 'total_drills_completed', 0),
                    'total_training_time': getattr(progress, 'total_training_time', getattr(progress, 'total_time_all_sessions', 0)),
                    'current_streak': progress.current_streak,
                    'longest_streak': getattr(progress, 'longest_streak', getattr(progress, 'highest_streak', 0)),
                    'previous_streak': getattr(progress, 'previous_streak', 0),
                    'favorite_drill': getattr(progress, 'favorite_drill', ''),
                    'drills_per_session': getattr(progress, 'drills_per_session', 0.0),
                    'minutes_per_session': getattr(progress, 'minutes_per_session', 0.0),
                    'dribbling_drills_completed': getattr(progress, 'dribbling_drills_completed', 0),
                    'first_touch_drills_completed': getattr(progress, 'first_touch_drills_completed', 0),
                    'passing_drills_completed': getattr(progress, 'passing_drills_completed', 0),
                    'shooting_drills_completed': getattr(progress, 'shooting_drills_completed', 0),
                    'defending_drills_completed': getattr(progress, 'defending_drills_completed', 0),
                    'goalkeeping_drills_completed': getattr(progress, 'goalkeeping_drills_completed', 0),
                    'fitness_drills_completed': getattr(progress, 'fitness_drills_completed', 0),
                    'most_improved_skill': getattr(progress, 'most_improved_skill', ''),
                    'unique_drills_completed': getattr(progress, 'unique_drills_completed', 0),
                    'beginner_drills_completed': getattr(progress, 'beginner_drills_completed', 0),
                    'intermediate_drills_completed': getattr(progress, 'intermediate_drills_completed', 0),
                    'advanced_drills_completed': getattr(progress, 'advanced_drills_completed', 0),
                    'mental_training_sessions': getattr(progress, 'mental_training_sessions', 0),
                    'total_mental_training_minutes': getattr(progress, 'total_mental_training_minutes', 0),
                    'last_training_date': getattr(progress, 'last_training_date', None),
                    'last_training_date_iso': progress.last_training_date.isoformat() if getattr(progress, 'last_training_date', None) else None,
                    'created_at': getattr(progress, 'created_at', None),
                    'created_at_iso': progress.created_at.isoformat() if getattr(progress, 'created_at', None) else None,
                    'updated_at': progress.updated_at.isoformat() if progress.updated_at else None
                }
            
            
            # Get refresh tokens
            refresh_tokens = self.v2_session.query(RefreshToken).filter(RefreshToken.user_id == user.id).all()
            user_data['refresh_tokens'] = [
                {
                    'id': token.id,
                    'token': token.token,
                    'expires_at': token.expires_at.isoformat() if token.expires_at else None,
                    'created_at': token.created_at.isoformat() if token.created_at else None
                }
                for token in refresh_tokens
            ]
            
            # Get password reset codes
            password_codes = self.v2_session.query(PasswordResetCode).filter(PasswordResetCode.user_id == user.id).all()
            user_data['password_reset_codes'] = [
                {
                    'id': code.id,
                    'code': code.code,
                    'expires_at': code.expires_at.isoformat() if code.expires_at else None,
                    'created_at': code.created_at.isoformat() if code.created_at else None
                }
                for code in password_codes
            ]
            
            # Get email verification codes
            email_codes = self.v2_session.query(EmailVerificationCode).filter(EmailVerificationCode.user_id == user.id).all()
            user_data['email_verification_codes'] = [
                {
                    'id': code.id,
                    'code': code.code,
                    'expires_at': code.expires_at.isoformat() if code.expires_at else None,
                    'created_at': code.created_at.isoformat() if code.created_at else None
                }
                for code in email_codes
            ]
            
            # Get mental training sessions
            mental_sessions = self.v2_session.query(MentalTrainingSession).filter(MentalTrainingSession.user_id == user.id).all()
            user_data['mental_training_sessions'] = [
                {
                    'id': session.id,
                    'date': session.date.isoformat() if session.date else None,
                    'duration_minutes': session.duration_minutes,
                    'session_type': session.session_type
                }
                for session in mental_sessions
            ]
            
            return user_data
            
        except Exception as e:
            logger.error(f"Error getting user data for {user.email}: {e}")
            self.v2_session.rollback()
            return {}
    
    def migrate_apple_users(self, platform_info: dict) -> bool:
        """Migrate Apple users from V1 to V2"""
        try:
            logger.info("Starting Apple user migration...")
            
            # Get user lists
            apple_in_both = platform_info.get('apple_emails_in_both', set())
            apple_only_v1 = platform_info.get('apple_emails_only_v1', set())
            
            # We're already limited to first 5 and last 5 users from V1, so no additional limiting needed
            logger.info(f"Processing {len(apple_in_both)} users to update and {len(apple_only_v1)} users to create")
            
            # Migrate Apple users that exist in both V1 and V2 (overwrite stale data)
            for email in apple_in_both:
                try:
                    if self._migrate_apple_user_overwrite(email):
                        self.stats['apple_users_updated'] += 1
                        logger.info(f"Updated Apple user: {email}")
                    else:
                        logger.error(f"Failed to update Apple user: {email}")
                        self.stats['errors'].append(f"Failed to update Apple user: {email}")
                except Exception as e:
                    logger.error(f"Error migrating Apple user {email}: {e}")
                    self.stats['errors'].append(f"Error migrating Apple user {email}: {e}")
            
            # Migrate Apple users that only exist in V1 (create new entries)
            for email in apple_only_v1:
                try:
                    if self._migrate_apple_user_create(email):
                        self.stats['apple_users_created'] += 1
                        logger.info(f"Created Apple user: {email}")
                    else:
                        logger.error(f"Failed to create Apple user: {email}")
                        self.stats['errors'].append(f"Failed to create Apple user: {email}")
                except Exception as e:
                    logger.error(f"Error creating Apple user {email}: {e}")
                    self.stats['errors'].append(f"Error creating Apple user {email}: {e}")
            
            logger.info(f"✅ Apple user migration completed:")
            logger.info(f"  Updated: {self.stats['apple_users_updated']}")
            logger.info(f"  Created: {self.stats['apple_users_created']}")
            logger.info(f"  Errors: {len(self.stats['errors'])}")
            
            # Consider migration successful if we processed users successfully
            # Errors like "user not found in V1" are expected for Android users
            total_processed = self.stats['apple_users_updated'] + self.stats['apple_users_created']
            success = total_processed > 0
            
            if success:
                logger.info("✅ Apple user migration successful")
            else:
                logger.error("❌ Apple user migration failed - no users processed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in Apple user migration: {e}")
            self.stats['errors'].append(f"Apple user migration failed: {e}")
            return False
    
    def _migrate_apple_user_overwrite(self, email: str) -> bool:
        """Migrate Apple user by deleting stale V2 data and creating fresh entries with new IDs"""
        try:
            # Get user from V1 (current data) - use case-insensitive search
            v1_user = self.v1_session.query(UserV1).filter(UserV1.email.ilike(email)).first()
            if not v1_user:
                logger.error(f"Apple user not found in V1: {email}")
                return False
            
            # Get user from V2 (stale data) - use case-insensitive search
            v2_user = self.v2_session.query(User).filter(User.email.ilike(email)).first()
            if not v2_user:
                logger.error(f"Apple user not found in V2: {email}")
                return False
            
            logger.info(f"Migrating Apple user {email} - deleting stale data and creating fresh entries")
            
            # Store the email for reference after deletion
            user_email = v2_user.email
            
            try:
                # Step 1: Delete all stale data for this user
                logger.info(f"Step 1: Deleting all stale data for {user_email}")
                self._delete_all_user_data(v2_user)
                logger.info(f"Step 1 completed: All stale data deleted for {user_email}")
                
                # Step 2: Create fresh user entry with new ID
                logger.info(f"Step 2: Creating fresh user entry for {user_email}")
                # Use the exact email that was deleted to avoid case sensitivity issues
                new_user = self._create_fresh_user_entry(v1_user, user_email)
                logger.info(f"Step 2 completed: Created fresh user entry with ID {new_user.id}")
                
                # Step 3: Migrate all related data with new user ID
                logger.info(f"Step 3: Migrating related data for {user_email}")
                self._migrate_user_related_data_fresh(v1_user, new_user)
                logger.info(f"Step 3 completed: All related data migrated for {user_email}")
                
                # Step 4: Commit all changes
                logger.info(f"Step 4: Committing all changes for {user_email}")
                self.v2_session.commit()
                logger.info(f"Successfully migrated {user_email} with new ID: {new_user.id}")
                return True
                
            except Exception as step_error:
                logger.error(f"Error in migration steps for {user_email}: {step_error}")
                logger.error(f"Step that failed: {step_error}")
                raise  # Re-raise to be caught by outer exception handler
            
        except Exception as e:
            logger.error(f"Error migrating Apple user {email}: {e}")
            try:
                self.v2_session.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback for {email}: {rollback_error}")
                # Create a fresh session if rollback fails
                self._create_fresh_v2_session()
            return False
    
    def _bulk_insert_sessions(self, sessions_data: List[dict]) -> None:
        """Bulk insert completed sessions for better performance."""
        if not sessions_data:
            return
            
        try:
            # Use bulk insert for sessions
            self.v2_session.execute(
                CompletedSession.__table__.insert(),
                sessions_data
            )
            logger.info(f"Bulk inserted {len(sessions_data)} completed sessions")
        except Exception as e:
            logger.error(f"Error bulk inserting sessions: {e}")
            raise

    def _bulk_insert_preferences(self, preferences_data: List[dict]) -> None:
        """Bulk insert session preferences for better performance."""
        if not preferences_data:
            return
            
        try:
            # Use bulk insert for preferences
            self.v2_session.execute(
                SessionPreferences.__table__.insert(),
                preferences_data
            )
            logger.info(f"Bulk inserted {len(preferences_data)} session preferences")
        except Exception as e:
            logger.error(f"Error bulk inserting preferences: {e}")
            raise

    def _bulk_insert_drill_groups(self, drill_groups_data: List[dict]) -> None:
        """Bulk insert drill groups for better performance."""
        if not drill_groups_data:
            return
            
        try:
            # Use bulk insert for drill groups
            self.v2_session.execute(
                DrillGroup.__table__.insert(),
                drill_groups_data
            )
            logger.info(f"Bulk inserted {len(drill_groups_data)} drill groups")
        except Exception as e:
            logger.error(f"Error bulk inserting drill groups: {e}")
            raise

    def _bulk_insert_drill_group_items(self, drill_items_data: List[dict]) -> None:
        """Bulk insert drill group items for better performance."""
        if not drill_items_data:
            return
            
        try:
            # Use bulk insert for drill group items
            self.v2_session.execute(
                DrillGroupItem.__table__.insert(),
                drill_items_data
            )
            logger.info(f"Bulk inserted {len(drill_items_data)} drill group items")
        except Exception as e:
            logger.error(f"Error bulk inserting drill group items: {e}")
            raise

    def _bulk_insert_progress_history(self, progress_data: List[dict]) -> None:
        """Bulk insert progress history for better performance."""
        if not progress_data:
            return
            
        try:
            # Use bulk insert for progress history
            self.v2_session.execute(
                ProgressHistory.__table__.insert(),
                progress_data
            )
            logger.info(f"Bulk inserted {len(progress_data)} progress history records")
        except Exception as e:
            logger.error(f"Error bulk inserting progress history: {e}")
            raise

    def _bulk_insert_password_reset_codes(self, reset_codes_data: List[dict]) -> None:
        """Bulk insert password reset codes for better performance."""
        if not reset_codes_data:
            return
            
        try:
            # Use bulk insert for password reset codes
            self.v2_session.execute(
                PasswordResetCode.__table__.insert(),
                reset_codes_data
            )
            logger.info(f"Bulk inserted {len(reset_codes_data)} password reset codes")
        except Exception as e:
            logger.error(f"Error bulk inserting password reset codes: {e}")
            raise

    def _bulk_insert_training_sessions(self, training_sessions_data: List[dict]) -> None:
        """Bulk insert training sessions for better performance."""
        if not training_sessions_data:
            return
            
        try:
            # Use bulk insert for training sessions
            self.v2_session.execute(
                TrainingSession.__table__.insert(),
                training_sessions_data
            )
            logger.info(f"Bulk inserted {len(training_sessions_data)} training sessions")
        except Exception as e:
            logger.error(f"Error bulk inserting training sessions: {e}")
            raise

    def _bulk_insert_ordered_session_drills(self, ordered_drills_data: List[dict]) -> None:
        """Bulk insert ordered session drills for better performance."""
        if not ordered_drills_data:
            return
            
        try:
            # Use bulk insert for ordered session drills
            self.v2_session.execute(
                OrderedSessionDrill.__table__.insert(),
                ordered_drills_data
            )
            logger.info(f"Bulk inserted {len(ordered_drills_data)} ordered session drills")
        except Exception as e:
            logger.error(f"Error bulk inserting ordered session drills: {e}")
            raise
    
    def _migrate_apple_user_create(self, email: str) -> bool:
        """Migrate Apple user by creating new entry in V2"""
        try:
            # Get user from V1 - use case-insensitive search
            v1_user = self.v1_session.query(UserV1).filter(UserV1.email.ilike(email)).first()
            if not v1_user:
                logger.error(f"Apple user not found in V1: {email}")
                return False
            
            logger.info(f"Creating fresh Apple user {email}")
            
            # Create fresh user entry with new ID
            new_user = self._create_fresh_user_entry(v1_user)
            
            # Migrate all related data with new user ID
            self._migrate_user_related_data_fresh(v1_user, new_user)
            
            self.v2_session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error creating Apple user {email}: {e}")
            try:
                self.v2_session.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback for {email}: {rollback_error}")
                # Create a fresh session if rollback fails
                self._create_fresh_v2_session()
            return False
    
    
    def _delete_all_user_data(self, user: User):
        """Delete ALL user data including the user record itself"""
        try:
            from sqlalchemy import text
            
            user_id = user.id
            user_email = user.email  # Store email before deletion
            logger.info(f"Deleting all data for user {user_email} (ID: {user_id})")
            
            # Delete related data in correct order to respect foreign key constraints
            delete_queries = [
                "DELETE FROM ordered_session_drills WHERE session_id IN (SELECT id FROM training_sessions WHERE user_id = :user_id)",
                "DELETE FROM training_sessions WHERE user_id = :user_id",
                "DELETE FROM completed_sessions WHERE user_id = :user_id",
                "DELETE FROM session_preferences WHERE user_id = :user_id", 
                "DELETE FROM drill_group_items WHERE drill_group_id IN (SELECT id FROM drill_groups WHERE user_id = :user_id)",
                "DELETE FROM drill_groups WHERE user_id = :user_id",
                "DELETE FROM progress_history WHERE user_id = :user_id",
                "DELETE FROM refresh_tokens WHERE user_id = :user_id",
                "DELETE FROM password_reset_codes WHERE user_id = :user_id",
                "DELETE FROM email_verification_codes WHERE user_id = :user_id",
                "DELETE FROM mental_training_sessions WHERE user_id = :user_id",
                "DELETE FROM custom_drills WHERE user_id = :user_id",
                "DELETE FROM saved_filters WHERE user_id = :user_id",
                "DELETE FROM users WHERE id = :user_id"
            ]
            
            for query in delete_queries:
                self.v2_session.execute(text(query), {"user_id": user_id})
            
            # Reset sequences after deletion to avoid ID conflicts
            sequence_resets = [
                "SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM users), false)",
                "SELECT setval('completed_sessions_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM completed_sessions), false)",
                "SELECT setval('session_preferences_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM session_preferences), false)",
                "SELECT setval('drill_groups_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM drill_groups), false)",
                "SELECT setval('drill_group_items_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM drill_group_items), false)",
                "SELECT setval('progress_history_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM progress_history), false)",
                "SELECT setval('refresh_tokens_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM refresh_tokens), false)",
                "SELECT setval('mental_training_sessions_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM mental_training_sessions), false)",
                "SELECT setval('training_sessions_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM training_sessions), false)",
                "SELECT setval('ordered_session_drills_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM ordered_session_drills), false)",
                "SELECT setval('custom_drills_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM custom_drills), false)",
                "SELECT setval('saved_filters_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM saved_filters), false)"
            ]
            
            for reset_query in sequence_resets:
                self.v2_session.execute(text(reset_query))
            
            # Commit the deletions and sequence resets immediately
            self.v2_session.commit()
            logger.info(f"Successfully deleted all data for user {user_email} and reset sequences")
            
        except Exception as e:
            logger.error(f"Error deleting all user data for {user_email}: {e}")
            self.v2_session.rollback()
            raise
    
    def _create_fresh_user_entry(self, v1_user: UserV1, email: str = None) -> User:
        """Create a fresh user entry with new ID"""
        try:
            from datetime import datetime
            
            new_user = User(
                first_name=v1_user.first_name,
                last_name=v1_user.last_name,
                email=email or v1_user.email,
                hashed_password=v1_user.hashed_password,
                primary_goal=v1_user.primary_goal,
                biggest_challenge=v1_user.biggest_challenge,
                training_experience=v1_user.training_experience,
                position=v1_user.position,
                playstyle=v1_user.playstyle,
                age_range=v1_user.age_range,
                strengths=v1_user.strengths,
                areas_to_improve=v1_user.areas_to_improve,
                training_location=v1_user.training_location,
                available_equipment=v1_user.available_equipment,
                daily_training_time=v1_user.daily_training_time,
                weekly_training_days=v1_user.weekly_training_days
            )
            
            # Don't set ID - let database generate new one
            new_user.id = None
            
            # Reset user sequence to avoid conflicts
            from sqlalchemy import text
            self.v2_session.execute(text("SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM users), false)"))
            
            self.v2_session.add(new_user)
            self.v2_session.flush()  # Get the new ID
            
            logger.info(f"Created fresh user entry with new ID: {new_user.id}")
            return new_user
            
        except Exception as e:
            logger.error(f"Error creating fresh user entry: {e}")
            raise
    
    def _migrate_user_related_data_fresh(self, v1_user: UserV1, new_user: User):
        """Migrate all related data with fresh user ID using bulk operations for better performance"""
        try:
            logger.info(f"Migrating related data for fresh user {new_user.email} (ID: {new_user.id})")
            
            # Migrate completed sessions (if they exist) - BULK OPERATION
            completed_sessions = getattr(v1_user, 'completed_sessions', [])
            logger.info(f"Found {len(completed_sessions)} completed sessions to migrate")
            
            if completed_sessions:
                sessions_data = []
                for session in completed_sessions:
                    logger.info(f"Processing completed session from {session.date} with drills: {session.drills}")
                    # Fix the drills JSON to use correct UUIDs
                    fixed_drills_json = self._fix_drills_json_uuids(session.drills)
                    logger.info(f"Fixed drills JSON: {fixed_drills_json}")
                    
                    sessions_data.append({
                        'user_id': new_user.id,  # Use new user ID
                        'date': session.date,
                        'session_type': getattr(session, 'session_type', 'drill_training'),
                        'total_completed_drills': session.total_completed_drills,
                        'total_drills': session.total_drills,
                        'drills': fixed_drills_json,  # Use the fixed JSON with correct UUIDs
                        'duration_minutes': getattr(session, 'duration_minutes', None),
                        'mental_training_session_id': getattr(session, 'mental_training_session_id', None)
                    })
                
                # Bulk insert all sessions at once
                self._bulk_insert_sessions(sessions_data)
            
            # Migrate session preferences (if they exist) - BULK OPERATION
            session_prefs = getattr(v1_user, 'session_preferences', None)
            if session_prefs:
                preferences_data = [{
                    'user_id': new_user.id,  # Use new user ID
                    'duration': session_prefs.duration,
                    'available_equipment': session_prefs.available_equipment,
                    'training_style': session_prefs.training_style,
                    'training_location': session_prefs.training_location,
                    'difficulty': session_prefs.difficulty,
                    'target_skills': session_prefs.target_skills,
                    'created_at': getattr(session_prefs, 'created_at', None),
                    'updated_at': getattr(session_prefs, 'updated_at', None)
                }]
                
                # Bulk insert preferences
                self._bulk_insert_preferences(preferences_data)
            
            # Migrate drill groups (if they exist) - BULK OPERATION
            drill_groups = getattr(v1_user, 'drill_groups', [])
            if drill_groups:
                # First, bulk insert all drill groups
                drill_groups_data = []
                for group in drill_groups:
                    drill_groups_data.append({
                        'user_id': new_user.id,  # Use new user ID
                        'name': group.name,
                        'description': group.description,
                        'is_liked_group': group.is_liked_group
                    })
                
                # Bulk insert drill groups
                self._bulk_insert_drill_groups(drill_groups_data)
                
                # Get the newly inserted drill groups to get their IDs
                self.v2_session.flush()
                new_drill_groups = self.v2_session.query(DrillGroup).filter(
                    DrillGroup.user_id == new_user.id
                ).all()
                
                # Now bulk insert drill group items
                drill_items_data = []
                for i, group in enumerate(drill_groups):
                    new_group = new_drill_groups[i]  # Match by order
                    drill_items = getattr(group, 'drill_items', [])
                    
                    for item in drill_items:
                        # Map V1 drill_id to V2 drill_uuid
                        drill_uuid = self._map_drill_id_to_uuid(item.drill_id)
                        
                        drill_items_data.append({
                            'drill_group_id': new_group.id,  # Use new group ID
                            'drill_uuid': drill_uuid,  # Map V1 drill_id to V2 drill_uuid
                            'position': item.position,
                            'created_at': getattr(item, 'created_at', None)
                        })
                
                # Bulk insert drill group items
                if drill_items_data:
                    self._bulk_insert_drill_group_items(drill_items_data)
            
            # Migrate progress history (if it exists) - use enhanced calculation - BULK OPERATION
            progress_history = getattr(v1_user, 'progress_history', None)
            if progress_history:
                # First, we need to get the completed sessions we just migrated to calculate proper metrics
                # Flush the session to ensure completed sessions are in the database
                self.v2_session.flush()
                
                # Query the completed sessions we just migrated
                migrated_completed_sessions = self.v2_session.query(CompletedSession).filter(
                    CompletedSession.user_id == new_user.id
                ).all()
                
                # Calculate enhanced progress metrics using the actual completed sessions
                from routers.data_sync_updates import calculate_enhanced_progress_metrics
                enhanced_metrics = calculate_enhanced_progress_metrics(migrated_completed_sessions, new_user.position)
                
                progress_data = [{
                    'user_id': new_user.id,  # Use new user ID
                    'completed_sessions_count': len(migrated_completed_sessions),  # Use actual count from migrated sessions
                    'current_streak': progress_history.current_streak,  # Keep V1 streak data
                    'highest_streak': progress_history.highest_streak,  # Keep V1 streak data
                    'previous_streak': getattr(progress_history, 'previous_streak', 0),  # Keep V1 streak data
                    'favorite_drill': enhanced_metrics.get('favorite_drill', ''),
                    'drills_per_session': enhanced_metrics.get('drills_per_session', 0.0),
                    'minutes_per_session': enhanced_metrics.get('minutes_per_session', 0.0),
                    'total_time_all_sessions': enhanced_metrics.get('total_time_all_sessions', 0),
                    'dribbling_drills_completed': enhanced_metrics.get('dribbling_drills_completed', 0),
                    'first_touch_drills_completed': enhanced_metrics.get('first_touch_drills_completed', 0),
                    'passing_drills_completed': enhanced_metrics.get('passing_drills_completed', 0),
                    'shooting_drills_completed': enhanced_metrics.get('shooting_drills_completed', 0),
                    'defending_drills_completed': enhanced_metrics.get('defending_drills_completed', 0),
                    'goalkeeping_drills_completed': enhanced_metrics.get('goalkeeping_drills_completed', 0),
                    'fitness_drills_completed': enhanced_metrics.get('fitness_drills_completed', 0),
                    'most_improved_skill': enhanced_metrics.get('most_improved_skill', ''),
                    'unique_drills_completed': enhanced_metrics.get('unique_drills_completed', 0),
                    'beginner_drills_completed': enhanced_metrics.get('beginner_drills_completed', 0),
                    'intermediate_drills_completed': enhanced_metrics.get('intermediate_drills_completed', 0),
                    'advanced_drills_completed': enhanced_metrics.get('advanced_drills_completed', 0),
                    'mental_training_sessions': enhanced_metrics.get('mental_training_sessions', 0),
                    'total_mental_training_minutes': enhanced_metrics.get('total_mental_training_minutes', 0),
                    'updated_at': getattr(progress_history, 'updated_at', None)
                }]
                
                # Bulk insert progress history
                self._bulk_insert_progress_history(progress_data)
                logger.info(f"Created progress history with enhanced metrics for user {new_user.email}")
            
            # Migrate refresh tokens (if they exist) - BULK OPERATION
            refresh_tokens = getattr(v1_user, 'refresh_tokens', [])
            if refresh_tokens:
                tokens_data = []
                for token in refresh_tokens:
                    # Check if token already exists to avoid unique constraint violation
                    existing_token = self.v2_session.query(RefreshToken).filter(
                        RefreshToken.token == token.token
                    ).first()
                    
                    if not existing_token:
                        tokens_data.append({
                            'user_id': new_user.id,  # Use new user ID
                            'token': token.token,
                            'expires_at': token.expires_at,
                            'created_at': token.created_at,
                            'is_revoked': getattr(token, 'is_revoked', False)
                        })
                    else:
                        logger.info(f"Skipping duplicate refresh token for user {new_user.email}")
                
                # Bulk insert refresh tokens
                if tokens_data:
                    self.v2_session.execute(
                        RefreshToken.__table__.insert(),
                        tokens_data
                    )
                    logger.info(f"Bulk inserted {len(tokens_data)} refresh tokens")
            
            # Migrate password reset codes (if they exist) - BULK OPERATION
            password_reset_codes = getattr(v1_user, 'password_reset_codes', [])
            if password_reset_codes:
                reset_codes_data = []
                for code in password_reset_codes:
                    reset_codes_data.append({
                        'user_id': new_user.id,  # Use new user ID
                        'code': code.code,
                        'expires_at': code.expires_at,
                        'created_at': code.created_at
                    })
                
                # Bulk insert password reset codes
                self._bulk_insert_password_reset_codes(reset_codes_data)
            
            
            # Migrate training sessions and their ordered drills - BULK OPERATION
            training_sessions = getattr(v1_user, 'training_sessions', [])
            if training_sessions:
                # First, bulk insert all training sessions
                training_sessions_data = []
                for ts in training_sessions:
                    training_sessions_data.append({
                        'user_id': new_user.id,  # Use new user ID
                        'total_duration': ts.total_duration,
                        'focus_areas': ts.focus_areas,
                        'created_at': getattr(ts, 'created_at', None)
                    })
                
                # Bulk insert training sessions
                self._bulk_insert_training_sessions(training_sessions_data)
                
                # Get the newly inserted training sessions to get their IDs
                self.v2_session.flush()
                new_training_sessions = self.v2_session.query(TrainingSession).filter(
                    TrainingSession.user_id == new_user.id
                ).all()
                
                # Now bulk insert ordered session drills
                ordered_drills_data = []
                for i, ts in enumerate(training_sessions):
                    new_training_session = new_training_sessions[i]  # Match by order
                    ordered_drills = getattr(ts, 'ordered_drills', [])
                    
                    for od in ordered_drills:
                        # Map V1 drill_id to V2 drill_uuid
                        drill_uuid = self._map_drill_id_to_uuid(od.drill_id)
                        
                        ordered_drills_data.append({
                            'session_id': new_training_session.id,  # Use new training session ID
                            'drill_uuid': drill_uuid,  # Map V1 drill_id to V2 drill_uuid
                            'position': od.position,
                            'sets_done': od.sets_done if od.sets_done is not None else 0,  # Default to 0 if null
                            'sets': od.sets,
                            'reps': od.reps,
                            'rest': od.rest,
                            'duration': od.duration,
                            'is_completed': od.is_completed
                        })
                
                # Bulk insert ordered session drills
                if ordered_drills_data:
                    self._bulk_insert_ordered_session_drills(ordered_drills_data)
            
            logger.info(f"Successfully migrated all related data for fresh user {new_user.email}")
            
        except Exception as e:
            logger.error(f"Error migrating related data for fresh user: {e}")
            raise
    
    def _map_drill_id_to_uuid(self, v1_drill_id: int) -> str:
        """Map V1 drill_id to V2 drill_uuid"""
        try:
            from sqlalchemy import text
            
            # Query the V2 drills table to find the drill with matching ID
            # Note: V2 drills table has both id and uuid columns
            query = text("SELECT uuid FROM drills WHERE id = :drill_id")
            result = self.v2_session.execute(query, {"drill_id": v1_drill_id}).fetchone()
            
            if result:
                drill_uuid = str(result[0])
                logger.info(f"Mapped V1 drill_id {v1_drill_id} to V2 drill_uuid {drill_uuid}")
                return drill_uuid
            else:
                logger.warning(f"No V2 drill found for V1 drill_id {v1_drill_id}, setting drill_uuid to None")
                return None
            
        except Exception as e:
            logger.error(f"Error mapping drill_id {v1_drill_id} to UUID: {e}")
            return None
    
    def _fix_drills_json_uuids(self, drills_json: list) -> list:
        """Fix drill UUIDs in the drills JSON by matching drill names"""
        try:
            if not drills_json or not isinstance(drills_json, list):
                return drills_json
            
            fixed_drills = []
            for drill_entry in drills_json:
                if not isinstance(drill_entry, dict):
                    fixed_drills.append(drill_entry)
                    continue
                
                # Check if drill info is nested under 'drill' key (V2 format)
                drill_info = drill_entry.get('drill', drill_entry)
                if not isinstance(drill_info, dict):
                    fixed_drills.append(drill_entry)
                    continue
                
                drill_name = drill_info.get('title') or drill_info.get('name')
                if not drill_name:
                    logger.warning(f"Drill data missing name/title: {drill_info}")
                    fixed_drills.append(drill_entry)
                    continue
                
                # Find the drill by name in V2 database
                from sqlalchemy import text
                query = text("SELECT uuid FROM drills WHERE title = :drill_name")
                result = self.v2_session.execute(query, {"drill_name": drill_name}).fetchone()
                
                if result:
                    new_drill_uuid = str(result[0])
                    old_drill_uuid = drill_info.get('uuid') or drill_info.get('id', 'unknown')
                    
                    # Create a copy of the drill entry and update the UUID
                    fixed_entry = drill_entry.copy()
                    if 'drill' in fixed_entry:
                        # Create new drill dict with uuid first
                        old_drill_data = fixed_entry['drill'].copy()
                        # Remove old ID fields
                        if 'id' in old_drill_data:
                            del old_drill_data['id']
                        if 'uuid' in old_drill_data:
                            del old_drill_data['uuid']
                        
                        # Create new drill dict with uuid at the beginning
                        new_drill_data = {'uuid': new_drill_uuid}
                        new_drill_data.update(old_drill_data)
                        fixed_entry['drill'] = new_drill_data
                    else:
                        # Create new dict with uuid first
                        old_data = fixed_entry.copy()
                        if 'id' in old_data:
                            del old_data['id']
                        if 'uuid' in old_data:
                            del old_data['uuid']
                        
                        new_data = {'uuid': new_drill_uuid}
                        new_data.update(old_data)
                        fixed_entry = new_data
                    
                    logger.info(f"Mapped drill '{drill_name}' from old UUID {old_drill_uuid} to new UUID {new_drill_uuid}")
                    fixed_drills.append(fixed_entry)
                else:
                    logger.warning(f"No V2 drill found with name '{drill_name}', keeping original data")
                    fixed_drills.append(drill_entry)
            
            return fixed_drills
            
        except Exception as e:
            logger.error(f"Error fixing drills JSON UUIDs: {e}")
            return drills_json
    
    
    def validate_migration(self) -> bool:
        """Validate that migration was successful"""
        try:
            logger.info("Validating migration...")
            
            platform_info = self.identify_user_platforms()
            
            # Check that all Apple users are now in V2 (sample first 50 for performance)
            apple_emails = platform_info.get('apple_emails_in_both', set()) | platform_info.get('apple_emails_only_v1', set())
            apple_emails_sample = list(apple_emails)[:50]  # Limit to first 50 users
            v2_apple_count = 0
            
            logger.info(f"Validating sample of {len(apple_emails_sample)} Apple users (out of {len(apple_emails)} total)")
            for email in apple_emails_sample:
                if self.v2_session.query(User).filter(User.email == email).first():
                    v2_apple_count += 1
            
            # Check that Android users are preserved (sample first 50 for performance)
            android_emails = platform_info.get('android_emails', set())
            android_emails_sample = list(android_emails)[:50]  # Limit to first 50 users
            v2_android_count = 0
            
            logger.info(f"Validating sample of {len(android_emails_sample)} Android users (out of {len(android_emails)} total)")
            for email in android_emails_sample:
                if self.v2_session.query(User).filter(User.email == email).first():
                    v2_android_count += 1
            
            validation_results = {
                'apple_users_migrated_sample': v2_apple_count,
                'apple_users_sample_size': len(apple_emails_sample),
                'apple_users_total': len(apple_emails),
                'android_users_preserved_sample': v2_android_count,
                'android_users_sample_size': len(android_emails_sample),
                'android_users_total': len(android_emails),
                'migration_successful': v2_apple_count == len(apple_emails_sample) and v2_android_count == len(android_emails_sample)
            }
            
            logger.info(f"Migration validation results: {validation_results}")
            
            if validation_results['migration_successful']:
                logger.info("✅ Migration validation passed")
            else:
                logger.error("❌ Migration validation failed")
            
            return validation_results['migration_successful']
            
        except Exception as e:
            logger.error(f"Error validating migration: {e}")
            return False
    
    def run_migration(self) -> bool:
        """Run the complete migration process"""
        try:
            logger.info("Starting V2 migration process...")
            
            # Step 1: Identify user platforms
            platform_info = self.identify_user_platforms()
            if not platform_info:
                logger.error("Failed to identify user platforms")
                return False
            
            # Step 2: Skip Android backup since we're only processing Apple users in this test
            logger.info("Skipping Android backup - only processing Apple users in this test")
            
            # Step 3: Migrate Apple users
            if not self.migrate_apple_users(platform_info):
                logger.error("Failed to migrate Apple users")
                return False
            
            # Step 4: Validate migration
            if not self.validate_migration():
                logger.error("Migration validation failed")
                return False
            
            # Step 5: Save migration report
            self._save_migration_report()
            
            logger.info("✅ V2 migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.stats['errors'].append(f"Migration failed: {e}")
            return False
        finally:
            self.v1_session.close()
            self.v2_session.close()
    
    def _save_migration_report(self):
        """Save migration report to file"""
        try:
            report = {
                'migration_date': datetime.now().isoformat(),
                'statistics': self.stats,
                'android_backup_count': len(self.android_backup),
                'config': {
                    'debug_mode': config.is_debug_mode(),
                    'max_test_users': config.get_test_user_limit() if config.is_debug_mode() else None
                }
            }
            
            report_path = config.get_backup_path("migration_report")
            with open(report_path.with_suffix('.json'), 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Migration report saved: {report_path}")
            
        except Exception as e:
            logger.error(f"Error saving migration report: {e}")

def main():
    """Main function for command line usage"""
    if len(sys.argv) != 3:
        print("Usage: python v2_migration_manager.py <v1_database_url> <v2_database_url>")
        print("Example: python v2_migration_manager.py <V1_DATABASE_URL> <V2_DATABASE_URL>")
        sys.exit(1)
    
    v1_url = sys.argv[1]
    v2_url = sys.argv[2]
    
    logger.info(f"Running V2 migration from {v1_url} to {v2_url}")
    
    manager = V2MigrationManager(v1_url, v2_url)
    
    if manager.run_migration():
        logger.info("Migration completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
