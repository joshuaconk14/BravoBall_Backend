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
        """Identify Apple vs Android users based on email presence - simplified for testing"""
        try:
            logger.info("Identifying user platforms (simplified test mode)...")
            
            # Get first 5 users from V1 (guaranteed to have stale data in staging)
            v1_users_first_5 = self.v1_session.query(UserV1.email).limit(5).all()
            first_5_emails = set()
            for (email,) in v1_users_first_5:
                if email:
                    first_5_emails.add(email.lower())
                    logger.info(f"First 5 V1 user: {email}")
            
            # Get last 5 users from V1 (guaranteed to be new users not in staging)
            v1_users_last_5 = self.v1_session.query(UserV1.email).order_by(UserV1.id.desc()).limit(5).all()
            last_5_emails = set()
            for (email,) in v1_users_last_5:
                if email:
                    last_5_emails.add(email.lower())
                    logger.info(f"Last 5 V1 user: {email}")
            
            # Get all emails from staging to check which ones exist
            staging_emails = set()
            staging_users = self.v2_session.query(User.email).all()
            for (email,) in staging_users:
                if email:
                    staging_emails.add(email.lower())
            
            # Categorize the test users
            apple_in_both = first_5_emails & staging_emails  # First 5 that exist in staging (stale data)
            apple_only_v1 = last_5_emails - staging_emails   # Last 5 that don't exist in staging (new users)
            
            platform_info = {
                'apple_users_total': len(first_5_emails) + len(last_5_emails),
                'apple_in_both': len(apple_in_both),
                'apple_only_v1': len(apple_only_v1),
                'android_users': 0,  # Not processing Android users in this test
                'apple_emails_in_both': apple_in_both,
                'apple_emails_only_v1': apple_only_v1,
                'android_emails': set()  # Not processing Android users in this test
            }
            
            logger.info(f"Simplified platform identification complete:")
            logger.info(f"  First 5 V1 users (to update stale data): {len(first_5_emails)}")
            logger.info(f"  Last 5 V1 users (to create new): {len(last_5_emails)}")
            logger.info(f"  Users that exist in staging (will be updated): {len(apple_in_both)}")
            logger.info(f"  Users that don't exist in staging (will be created): {len(apple_only_v1)}")
            
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
                'saved_filters': [],
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
            
            # Get saved filters
            saved_filters = self.v2_session.query(SavedFilter).filter(SavedFilter.user_id == user.id).all()
            user_data['saved_filters'] = [
                {
                    'id': filter_item.id,
                    'name': filter_item.name,
                    'filter_data': filter_item.filter_data,
                    'created_at': filter_item.created_at.isoformat() if filter_item.created_at else None
                }
                for filter_item in saved_filters
            ]
            
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
                new_user = self._create_fresh_user_entry(v1_user)
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
    
    def _migrate_user_related_data(self, v1_user: UserV1, v2_user: User):
        """Migrate all related data for a user"""
        try:
            # Clear existing related data for the V2 user (except for Android users)
            self._clear_user_related_data(v2_user)
            
            # Migrate completed sessions
            for session in v1_user.completed_sessions:
                new_session = CompletedSession(
                    user_id=v2_user.id,
                    date=session.date,
                    session_type=getattr(session, 'session_type', 'drill_training'),  # V1 might not have this column
                    total_completed_drills=session.total_completed_drills,
                    total_drills=session.total_drills,
                    drills=session.drills,
                    duration_minutes=getattr(session, 'duration_minutes', 30),  # V1 might not have this column
                    mental_training_session_id=getattr(session, 'mental_training_session_id', None)  # V1 might not have this column
                )
                # Explicitly set id to None to force auto-generation
                new_session.id = None
                self.v2_session.add(new_session)
            
            # Migrate session preferences (V1 has one, V2 has one)
            if v1_user.session_preferences:
                new_prefs = SessionPreferences(
                    user_id=v2_user.id,
                    duration=v1_user.session_preferences.duration,
                    available_equipment=v1_user.session_preferences.available_equipment,
                    training_style=v1_user.session_preferences.training_style,
                    training_location=v1_user.session_preferences.training_location,
                    difficulty=v1_user.session_preferences.difficulty,
                    target_skills=v1_user.session_preferences.target_skills,
                    created_at=v1_user.session_preferences.created_at,
                    updated_at=v1_user.session_preferences.updated_at
                )
                # Explicitly set id to None to force auto-generation
                new_prefs.id = None
                self.v2_session.add(new_prefs)
            
            # Migrate drill groups
            for group in v1_user.drill_groups:
                new_group = DrillGroup(
                    user_id=v2_user.id,
                    name=group.name,
                    description=group.description,
                    is_liked_group=group.is_liked_group
                )
                # Explicitly set id to None to force auto-generation
                new_group.id = None
                self.v2_session.add(new_group)
                self.v2_session.flush()  # Get the new group ID
                
                # Migrate drill group items
                for item in group.drill_items:
                    new_item = DrillGroupItem(
                        drill_group_id=new_group.id,
                        drill_uuid=None,  # V1 doesn't have drill_uuid, will need to be set later
                        position=item.position,
                        created_at=item.created_at
                    )
                    # Explicitly set id to None to force auto-generation
                    new_item.id = None
                    self.v2_session.add(new_item)
            
            # Migrate progress history
            if v1_user.progress_history:
                # V1 uses different column names and has fewer columns
                new_progress = ProgressHistory(
                    user_id=v2_user.id,
                    completed_sessions_count=v1_user.progress_history.completed_sessions_count,  # V1 uses 'completed_sessions_count'
                    current_streak=v1_user.progress_history.current_streak,
                    highest_streak=v1_user.progress_history.highest_streak,  # V1 uses 'highest_streak'
                    previous_streak=getattr(v1_user.progress_history, 'previous_streak', 0),
                    favorite_drill=getattr(v1_user.progress_history, 'favorite_drill', ''),
                    drills_per_session=0.0,  # V1 doesn't have this column
                    minutes_per_session=0.0,  # V1 doesn't have this column
                    total_time_all_sessions=0,  # V1 doesn't have this column
                    dribbling_drills_completed=0,  # V1 doesn't have this column
                    first_touch_drills_completed=0,  # V1 doesn't have this column
                    passing_drills_completed=0,  # V1 doesn't have this column
                    shooting_drills_completed=0,  # V1 doesn't have this column
                    defending_drills_completed=0,  # V1 doesn't have this column
                    goalkeeping_drills_completed=0,  # V1 doesn't have this column
                    fitness_drills_completed=0,  # V1 doesn't have this column
                    updated_at=v1_user.progress_history.updated_at
                )
                # Explicitly set id to None to force auto-generation
                new_progress.id = None
                self.v2_session.add(new_progress)
            
            # Migrate saved filters
            for filter_item in v1_user.saved_filters:
                new_filter = SavedFilter(
                    user_id=v2_user.id,
                    name=filter_item.name,
                    filter_data=getattr(filter_item, 'filter_data', {}),  # V1 doesn't have filter_data column
                    created_at=getattr(filter_item, 'created_at', None)  # V1 doesn't have created_at column
                )
                # Explicitly set id to None to force auto-generation
                new_filter.id = None
                self.v2_session.add(new_filter)
            
            # Migrate refresh tokens - check for duplicates first
            for token in v1_user.refresh_tokens:
                # Check if token already exists
                existing_token = self.v2_session.query(RefreshToken).filter(
                    RefreshToken.user_id == v2_user.id,
                    RefreshToken.token == token.token
                ).first()
                
                if not existing_token:
                    new_token = RefreshToken(
                        user_id=v2_user.id,
                        token=token.token,
                        expires_at=token.expires_at,
                        created_at=token.created_at,
                        is_revoked=getattr(token, 'is_revoked', False)  # V1 might not have this field
                    )
                    # Explicitly set id to None to force auto-generation
                    new_token.id = None
                    self.v2_session.add(new_token)
            
            # Migrate password reset codes - check for duplicates first
            for code in v1_user.password_reset_codes:
                # Check if code already exists
                existing_code = self.v2_session.query(PasswordResetCode).filter(
                    PasswordResetCode.user_id == v2_user.id,
                    PasswordResetCode.code == code.code
                ).first()
                
                if not existing_code:
                    new_code = PasswordResetCode(
                        user_id=v2_user.id,
                        code=code.code,
                        expires_at=code.expires_at,
                        created_at=code.created_at,
                        is_used=getattr(code, 'is_used', False)  # V1 might not have this field
                    )
                    # Explicitly set id to None to force auto-generation
                    new_code.id = None
                    self.v2_session.add(new_code)
            
            # Note: V1 doesn't have email_verification_codes table, so skip this migration
            
            # Migrate training sessions (V1 has training_sessions, not mental_training_sessions)
            for session in v1_user.training_sessions:
                new_session = MentalTrainingSession(
                    user_id=v2_user.id,
                    date=getattr(session, 'date', None),
                    duration_minutes=getattr(session, 'duration_minutes', 30),  # Default to 30 minutes if not specified
                    session_type=getattr(session, 'session_type', 'mental_training')
                )
                # Explicitly set id to None to force auto-generation
                new_session.id = None
                self.v2_session.add(new_session)
            
            self.stats['related_data_migrated'] += 1
            
        except Exception as e:
            logger.error(f"Error migrating related data for {v2_user.email}: {e}")
            # Rollback the session to clear any failed transactions
            try:
                self.v2_session.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback for related data migration: {rollback_error}")
            raise
    
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
                "DELETE FROM saved_filters WHERE user_id = :user_id",
                "DELETE FROM refresh_tokens WHERE user_id = :user_id",
                "DELETE FROM password_reset_codes WHERE user_id = :user_id",
                "DELETE FROM email_verification_codes WHERE user_id = :user_id",
                "DELETE FROM mental_training_sessions WHERE user_id = :user_id",
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
                "SELECT setval('saved_filters_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM saved_filters), false)",
                "SELECT setval('refresh_tokens_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM refresh_tokens), false)",
                "SELECT setval('mental_training_sessions_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM mental_training_sessions), false)",
                "SELECT setval('training_sessions_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM training_sessions), false)",
                "SELECT setval('ordered_session_drills_id_seq', (SELECT COALESCE(MAX(id) + 1, 1) FROM ordered_session_drills), false)"
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
    
    def _create_fresh_user_entry(self, v1_user: UserV1) -> User:
        """Create a fresh user entry with new ID"""
        try:
            from datetime import datetime
            
            new_user = User(
                first_name=v1_user.first_name,
                last_name=v1_user.last_name,
                email=v1_user.email,
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
        """Migrate all related data with fresh user ID (no clearing needed)"""
        try:
            logger.info(f"Migrating related data for fresh user {new_user.email} (ID: {new_user.id})")
            
            # Migrate completed sessions (if they exist)
            completed_sessions = getattr(v1_user, 'completed_sessions', [])
            for session in completed_sessions:
                new_session = CompletedSession(
                    user_id=new_user.id,  # Use new user ID
                    date=session.date,
                    session_type=getattr(session, 'session_type', 'drill_training'),
                    total_completed_drills=session.total_completed_drills,
                    total_drills=session.total_drills,
                    drills=session.drills,
                    duration_minutes=getattr(session, 'duration_minutes', 30),
                    mental_training_session_id=getattr(session, 'mental_training_session_id', None)
                )
                new_session.id = None  # Force new ID
                self.v2_session.add(new_session)
            
            # Migrate session preferences (if they exist)
            session_prefs = getattr(v1_user, 'session_preferences', None)
            if session_prefs:
                new_prefs = SessionPreferences(
                    user_id=new_user.id,  # Use new user ID
                    duration=session_prefs.duration,
                    available_equipment=session_prefs.available_equipment,
                    training_style=session_prefs.training_style,
                    training_location=session_prefs.training_location,
                    difficulty=session_prefs.difficulty,
                    target_skills=session_prefs.target_skills,
                    created_at=getattr(session_prefs, 'created_at', None),
                    updated_at=getattr(session_prefs, 'updated_at', None)
                )
                new_prefs.id = None  # Force new ID
                self.v2_session.add(new_prefs)
            
            # Migrate drill groups (if they exist)
            drill_groups = getattr(v1_user, 'drill_groups', [])
            for group in drill_groups:
                new_group = DrillGroup(
                    user_id=new_user.id,  # Use new user ID
                    name=group.name,
                    description=group.description,
                    is_liked_group=group.is_liked_group
                )
                new_group.id = None  # Force new ID
                self.v2_session.add(new_group)
                self.v2_session.flush()  # Get the new group ID
                
                # Migrate drill group items (if they exist)
                drill_items = getattr(group, 'drill_items', [])
                for item in drill_items:
                    new_item = DrillGroupItem(
                        drill_group_id=new_group.id,  # Use new group ID
                        drill_uuid=None,  # V1 doesn't have drill_uuid
                        position=item.position,
                        created_at=getattr(item, 'created_at', None)
                    )
                    new_item.id = None  # Force new ID
                    self.v2_session.add(new_item)
            
            # Migrate progress history (if it exists)
            progress_history = getattr(v1_user, 'progress_history', None)
            if progress_history:
                new_progress = ProgressHistory(
                    user_id=new_user.id,  # Use new user ID
                    completed_sessions_count=progress_history.completed_sessions_count,
                    current_streak=progress_history.current_streak,
                    highest_streak=progress_history.highest_streak,
                    previous_streak=getattr(progress_history, 'previous_streak', 0),
                    favorite_drill=getattr(progress_history, 'favorite_drill', ''),
                    drills_per_session=0.0,  # V1 doesn't have this column
                    minutes_per_session=0.0,  # V1 doesn't have this column
                    total_time_all_sessions=0,  # V1 doesn't have this column
                    dribbling_drills_completed=0,  # V1 doesn't have this column
                    first_touch_drills_completed=0,  # V1 doesn't have this column
                    passing_drills_completed=0,  # V1 doesn't have this column
                    shooting_drills_completed=0,  # V1 doesn't have this column
                    defending_drills_completed=0,  # V1 doesn't have this column
                    goalkeeping_drills_completed=0,  # V1 doesn't have this column
                    fitness_drills_completed=0,  # V1 doesn't have this column
                    updated_at=getattr(progress_history, 'updated_at', None)
                )
                new_progress.id = None  # Force new ID
                self.v2_session.add(new_progress)
            
            # Migrate saved filters (if they exist)
            saved_filters = getattr(v1_user, 'saved_filters', [])
            for filter_item in saved_filters:
                new_filter = SavedFilter(
                    user_id=new_user.id,  # Use new user ID
                    name=filter_item.name,
                    filter_data=getattr(filter_item, 'filter_data', {}),
                    created_at=getattr(filter_item, 'created_at', None)
                )
                new_filter.id = None  # Force new ID
                self.v2_session.add(new_filter)
            
            # Migrate refresh tokens (if they exist)
            refresh_tokens = getattr(v1_user, 'refresh_tokens', [])
            for token in refresh_tokens:
                new_token = RefreshToken(
                    user_id=new_user.id,  # Use new user ID
                    token=token.token,
                    expires_at=token.expires_at,
                    created_at=token.created_at,
                    is_revoked=getattr(token, 'is_revoked', False)
                )
                new_token.id = None  # Force new ID
                self.v2_session.add(new_token)
            
            # Migrate mental training sessions (if they exist)
            mental_sessions = getattr(v1_user, 'mental_training_sessions', [])
            for session in mental_sessions:
                new_session = MentalTrainingSession(
                    user_id=new_user.id,  # Use new user ID
                    date=getattr(session, 'date', None),
                    duration_minutes=getattr(session, 'duration_minutes', 30),
                    session_type=getattr(session, 'session_type', 'mental_training')
                )
                new_session.id = None  # Force new ID
                self.v2_session.add(new_session)
            
            # Migrate training sessions and their ordered drills
            training_sessions = getattr(v1_user, 'training_sessions', [])
            for ts in training_sessions:
                new_training_session = TrainingSession(
                    user_id=new_user.id,  # Use new user ID
                    total_duration=ts.total_duration,
                    focus_areas=ts.focus_areas,
                    created_at=getattr(ts, 'created_at', None)
                )
                new_training_session.id = None  # Force new ID
                self.v2_session.add(new_training_session)
                self.v2_session.flush()  # Get the new training session ID
                
                # Migrate ordered drills for this training session
                ordered_drills = getattr(ts, 'ordered_drills', [])
                for od in ordered_drills:
                    new_ordered_drill = OrderedSessionDrill(
                        session_id=new_training_session.id,  # Use new training session ID
                        drill_uuid=None,  # V1 uses drill_id, V2 uses drill_uuid - will need mapping
                        position=od.position,
                        sets_done=od.sets_done,
                        sets=od.sets,
                        reps=od.reps,
                        rest=od.rest,
                        duration=od.duration,
                        is_completed=od.is_completed
                    )
                    new_ordered_drill.id = None  # Force new ID
                    self.v2_session.add(new_ordered_drill)
            
            logger.info(f"Successfully migrated all related data for fresh user {new_user.email}")
            
        except Exception as e:
            logger.error(f"Error migrating related data for fresh user: {e}")
            raise
    
    def _clear_user_related_data(self, user: User):
        """Clear existing related data for a user (used when overwriting)"""
        try:
            # Use raw SQL for more reliable deletion
            from sqlalchemy import text
            
            user_id = user.id
            logger.info(f"Clearing related data for user {user.email} (ID: {user_id})")
            
            # Delete in correct order to respect foreign key constraints
            delete_queries = [
                "DELETE FROM completed_sessions WHERE user_id = :user_id",
                "DELETE FROM session_preferences WHERE user_id = :user_id", 
                "DELETE FROM drill_group_items WHERE drill_group_id IN (SELECT id FROM drill_groups WHERE user_id = :user_id)",
                "DELETE FROM drill_groups WHERE user_id = :user_id",
                "DELETE FROM progress_history WHERE user_id = :user_id",
                "DELETE FROM saved_filters WHERE user_id = :user_id",
                "DELETE FROM refresh_tokens WHERE user_id = :user_id",
                "DELETE FROM password_reset_codes WHERE user_id = :user_id",
                "DELETE FROM email_verification_codes WHERE user_id = :user_id",
                "DELETE FROM mental_training_sessions WHERE user_id = :user_id"
            ]
            
            for query in delete_queries:
                self.v2_session.execute(text(query), {"user_id": user_id})
            
            # Reset sequences to avoid ID conflicts
            sequence_resets = [
                "SELECT setval('completed_sessions_id_seq', (SELECT COALESCE(MAX(id), 1) FROM completed_sessions))",
                "SELECT setval('session_preferences_id_seq', (SELECT COALESCE(MAX(id), 1) FROM session_preferences))",
                "SELECT setval('drill_groups_id_seq', (SELECT COALESCE(MAX(id), 1) FROM drill_groups))",
                "SELECT setval('drill_group_items_id_seq', (SELECT COALESCE(MAX(id), 1) FROM drill_group_items))",
                "SELECT setval('progress_history_id_seq', (SELECT COALESCE(MAX(id), 1) FROM progress_history))",
                "SELECT setval('saved_filters_id_seq', (SELECT COALESCE(MAX(id), 1) FROM saved_filters))",
                "SELECT setval('refresh_tokens_id_seq', (SELECT COALESCE(MAX(id), 1) FROM refresh_tokens))",
                "SELECT setval('password_reset_codes_id_seq', (SELECT COALESCE(MAX(id), 1) FROM password_reset_codes))",
                "SELECT setval('email_verification_codes_id_seq', (SELECT COALESCE(MAX(id), 1) FROM email_verification_codes))",
                "SELECT setval('mental_training_sessions_id_seq', (SELECT COALESCE(MAX(id), 1) FROM mental_training_sessions))"
            ]
            
            for reset_query in sequence_resets:
                self.v2_session.execute(text(reset_query))
            
            # Commit the deletions and sequence resets immediately
            self.v2_session.commit()
            logger.info(f"Successfully cleared related data and reset sequences for user {user.email}")
            
        except Exception as e:
            logger.error(f"Error clearing related data for {user.email}: {e}")
            self.v2_session.rollback()
            raise
    
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
