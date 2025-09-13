#!/usr/bin/env python3
"""
simple_migration.py
Simplified migration script that focuses only on migrating 10 specific Apple users
from V1 to staging database (first 5 and last 5 users from V1)
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent))

from models_v1 import UserV1, CompletedSessionV1, SessionPreferencesV1, DrillGroupV1, ProgressHistoryV1
from models import User, CompletedSession, SessionPreferences, DrillGroup, ProgressHistory, RefreshToken, PasswordResetCode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(f'logs/simple_migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimpleMigration:
    """Simplified migration for 10 specific Apple users"""
    
    def __init__(self, v1_url: str, staging_url: str):
        self.v1_url = v1_url
        self.staging_url = staging_url
        
        # Create database connections
        self.v1_engine = create_engine(v1_url)
        self.staging_engine = create_engine(staging_url)
        self.v1_session = sessionmaker(bind=self.v1_engine)()
        self.staging_session = sessionmaker(bind=self.staging_engine)()
        
        # Migration results
        self.results = {
            'migrated_users': [],
            'errors': [],
            'summary': {}
        }
    
    def get_target_users(self) -> List[UserV1]:
        """Get first 5 and last 5 users from V1"""
        try:
            # Get total count
            total_count = self.v1_session.query(UserV1).count()
            logger.info(f"📊 Total V1 users: {total_count}")
            
            # Get first 5 users
            first_5 = self.v1_session.query(UserV1).order_by(UserV1.id.asc()).limit(5).all()
            logger.info(f"📋 First 5 users: {[user.email for user in first_5]}")
            
            # Get last 5 users
            last_5 = self.v1_session.query(UserV1).order_by(UserV1.id.desc()).limit(5).all()
            logger.info(f"📋 Last 5 users: {[user.email for user in last_5]}")
            
            # Combine and remove duplicates
            all_users = first_5 + last_5
            unique_users = []
            seen_emails = set()
            
            for user in all_users:
                if user.email and user.email not in seen_emails:
                    unique_users.append(user)
                    seen_emails.add(user.email)
            
            logger.info(f"🎯 Target users for migration: {len(unique_users)}")
            for user in unique_users:
                logger.info(f"  - {user.email} (ID: {user.id})")
            
            return unique_users
            
        except Exception as e:
            logger.error(f"❌ Error getting target users: {e}")
            return []
    
    def migrate_user(self, v1_user: UserV1) -> Dict[str, Any]:
        """Migrate a single user from V1 to staging"""
        result = {
            'email': v1_user.email,
            'v1_id': v1_user.id,
            'action': None,
            'staging_id': None,
            'error': None
        }
        
        try:
            # Check if user already exists in staging
            existing_user = self.staging_session.query(User).filter(User.email == v1_user.email).first()
            
            if existing_user:
                # Update existing user
                logger.info(f"🔄 Updating existing user: {v1_user.email}")
                self._update_user_data(existing_user, v1_user)
                result['action'] = 'updated'
                result['staging_id'] = existing_user.id
            else:
                # Create new user
                logger.info(f"➕ Creating new user: {v1_user.email}")
                new_user = self._create_user_from_v1(v1_user)
                self.staging_session.add(new_user)
                self.staging_session.flush()  # Get the ID
                result['action'] = 'created'
                result['staging_id'] = new_user.id
            
            # Commit the user
            self.staging_session.commit()
            logger.info(f"✅ Successfully migrated user: {v1_user.email}")
            
        except Exception as e:
            logger.error(f"❌ Error migrating user {v1_user.email}: {e}")
            self.staging_session.rollback()
            result['error'] = str(e)
        
        return result
    
    def _update_user_data(self, staging_user: User, v1_user: UserV1):
        """Update staging user with V1 data"""
        staging_user.first_name = v1_user.first_name
        staging_user.last_name = v1_user.last_name
        staging_user.hashed_password = v1_user.hashed_password
        staging_user.primary_goal = v1_user.primary_goal
        staging_user.biggest_challenge = v1_user.biggest_challenge
        staging_user.training_experience = v1_user.training_experience
        staging_user.position = v1_user.position
        staging_user.age_range = v1_user.age_range
        staging_user.strengths = v1_user.strengths
        staging_user.areas_to_improve = v1_user.areas_to_improve
        staging_user.training_location = v1_user.training_location
        staging_user.available_equipment = v1_user.available_equipment
        staging_user.daily_training_time = v1_user.daily_training_time
        staging_user.weekly_training_days = v1_user.weekly_training_days
        staging_user.playstyle = v1_user.playstyle
    
    def _create_user_from_v1(self, v1_user: UserV1) -> User:
        """Create new user in staging from V1 user"""
        new_user = User(
            email=v1_user.email,
            first_name=v1_user.first_name,
            last_name=v1_user.last_name,
            hashed_password=v1_user.hashed_password,
            primary_goal=v1_user.primary_goal,
            biggest_challenge=v1_user.biggest_challenge,
            training_experience=v1_user.training_experience,
            position=v1_user.position,
            age_range=v1_user.age_range,
            strengths=v1_user.strengths,
            areas_to_improve=v1_user.areas_to_improve,
            training_location=v1_user.training_location,
            available_equipment=v1_user.available_equipment,
            daily_training_time=v1_user.daily_training_time,
            weekly_training_days=v1_user.weekly_training_days,
            playstyle=v1_user.playstyle
        )
        return new_user
    
    def migrate_related_data(self, v1_user: UserV1, staging_user_id: int):
        """Migrate related data for a user (sessions, preferences, etc.)"""
        try:
            # Migrate completed sessions
            v1_sessions = self.v1_session.query(CompletedSessionV1).filter(
                CompletedSessionV1.user_id == v1_user.id
            ).all()
            
            for v1_session in v1_sessions:
                # Check if session already exists
                existing_session = self.staging_session.query(CompletedSession).filter(
                    CompletedSession.user_id == staging_user_id,
                    CompletedSession.date == v1_session.date
                ).first()
                
                if not existing_session:
                    new_session = CompletedSession(
                        user_id=staging_user_id,
                        date=v1_session.date,
                        session_type=getattr(v1_session, 'session_type', 'drill_training'),
                        total_completed_drills=v1_session.total_completed_drills,
                        total_drills=v1_session.total_drills,
                        drills=v1_session.drills,
                        duration_minutes=getattr(v1_session, 'duration_minutes', 0),
                        notes=getattr(v1_session, 'notes', '')
                    )
                    self.staging_session.add(new_session)
            
            # Migrate session preferences
            v1_prefs = self.v1_session.query(SessionPreferencesV1).filter(
                SessionPreferencesV1.user_id == v1_user.id
            ).first()
            
            if v1_prefs:
                existing_prefs = self.staging_session.query(SessionPreferences).filter(
                    SessionPreferences.user_id == staging_user_id
                ).first()
                
                if not existing_prefs:
                    new_prefs = SessionPreferences(
                        user_id=staging_user_id,
                        difficulty=v1_prefs.difficulty,
                        duration=v1_prefs.duration,
                        focus_areas=getattr(v1_prefs, 'focus_areas', []),
                        equipment=v1_prefs.equipment,
                        location=v1_prefs.location,
                        training_style=v1_prefs.training_style
                    )
                    self.staging_session.add(new_prefs)
            
            # Migrate drill groups
            v1_groups = self.v1_session.query(DrillGroupV1).filter(
                DrillGroupV1.user_id == v1_user.id
            ).all()
            
            for v1_group in v1_groups:
                existing_group = self.staging_session.query(DrillGroup).filter(
                    DrillGroup.user_id == staging_user_id,
                    DrillGroup.name == v1_group.name
                ).first()
                
                if not existing_group:
                    new_group = DrillGroup(
                        user_id=staging_user_id,
                        name=v1_group.name,
                        description=v1_group.description,
                        is_liked_group=v1_group.is_liked_group
                    )
                    self.staging_session.add(new_group)
            
            # Migrate progress history
            v1_progress = self.v1_session.query(ProgressHistoryV1).filter(
                ProgressHistoryV1.user_id == v1_user.id
            ).all()
            
            for v1_prog in v1_progress:
                existing_progress = self.staging_session.query(ProgressHistory).filter(
                    ProgressHistory.user_id == staging_user_id,
                    ProgressHistory.date == v1_prog.date
                ).first()
                
                if not existing_progress:
                    new_progress = ProgressHistory(
                        user_id=staging_user_id,
                        date=v1_prog.date,
                        total_drills_completed=v1_prog.total_drills_completed,
                        unique_drills_completed=v1_prog.unique_drills_completed,
                        total_time_all_sessions=v1_prog.total_time_all_sessions,
                        completed_sessions_count=v1_prog.completed_sessions_count,
                        current_streak=v1_prog.current_streak,
                        highest_streak=v1_prog.highest_streak
                    )
                    self.staging_session.add(new_progress)
            
            self.staging_session.commit()
            logger.info(f"✅ Migrated related data for user: {v1_user.email}")
            
        except Exception as e:
            logger.error(f"❌ Error migrating related data for {v1_user.email}: {e}")
            self.staging_session.rollback()
    
    def run_migration(self):
        """Run the complete migration"""
        logger.info("🚀 Starting simple migration of 10 Apple users...")
        
        try:
            # Get target users
            target_users = self.get_target_users()
            if not target_users:
                logger.error("❌ No target users found")
                return False
            
            # Migrate each user
            for v1_user in target_users:
                logger.info(f"🔄 Migrating user: {v1_user.email}")
                
                # Migrate user
                user_result = self.migrate_user(v1_user)
                self.results['migrated_users'].append(user_result)
                
                if user_result['error']:
                    self.results['errors'].append(f"User {v1_user.email}: {user_result['error']}")
                    continue
                
                # Migrate related data
                if user_result['staging_id']:
                    self.migrate_related_data(v1_user, user_result['staging_id'])
            
            # Generate summary
            self.generate_summary()
            
            # Save results
            self.save_results()
            
            logger.info("✅ Simple migration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            self.results['errors'].append(f"Migration failed: {e}")
            return False
    
    def generate_summary(self):
        """Generate migration summary"""
        total_users = len(self.results['migrated_users'])
        successful_users = len([u for u in self.results['migrated_users'] if not u['error']])
        updated_users = len([u for u in self.results['migrated_users'] if u['action'] == 'updated'])
        created_users = len([u for u in self.results['migrated_users'] if u['action'] == 'created'])
        
        self.results['summary'] = {
            'total_users': total_users,
            'successful_users': successful_users,
            'failed_users': total_users - successful_users,
            'updated_users': updated_users,
            'created_users': created_users,
            'success_rate': (successful_users / total_users * 100) if total_users > 0 else 0
        }
        
        logger.info("📊 Migration Summary:")
        logger.info(f"  Total users: {total_users}")
        logger.info(f"  Successful: {successful_users}")
        logger.info(f"  Failed: {total_users - successful_users}")
        logger.info(f"  Updated: {updated_users}")
        logger.info(f"  Created: {created_users}")
        logger.info(f"  Success rate: {self.results['summary']['success_rate']:.1f}%")
    
    def save_results(self):
        """Save migration results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backups/simple_migration_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"💾 Results saved to: {filename}")
    
    def validate_migration(self):
        """Validate that migration was successful"""
        logger.info("🔍 Validating migration results...")
        
        try:
            for user_result in self.results['migrated_users']:
                if user_result['error']:
                    continue
                
                email = user_result['email']
                staging_id = user_result['staging_id']
                
                # Check if user exists in staging
                staging_user = self.staging_session.query(User).filter(User.id == staging_id).first()
                if not staging_user:
                    logger.error(f"❌ User {email} not found in staging after migration")
                    continue
                
                # Check if email matches
                if staging_user.email != email:
                    logger.error(f"❌ Email mismatch for user {email}")
                    continue
                
                # Check related data
                sessions_count = self.staging_session.query(CompletedSession).filter(
                    CompletedSession.user_id == staging_id
                ).count()
                
                prefs_count = self.staging_session.query(SessionPreferences).filter(
                    SessionPreferences.user_id == staging_id
                ).count()
                
                groups_count = self.staging_session.query(DrillGroup).filter(
                    DrillGroup.user_id == staging_id
                ).count()
                
                progress_count = self.staging_session.query(ProgressHistory).filter(
                    ProgressHistory.user_id == staging_id
                ).count()
                
                logger.info(f"✅ User {email} validation:")
                logger.info(f"  - Sessions: {sessions_count}")
                logger.info(f"  - Preferences: {prefs_count}")
                logger.info(f"  - Drill groups: {groups_count}")
                logger.info(f"  - Progress records: {progress_count}")
            
            logger.info("✅ Migration validation completed")
            
        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple migration of 10 Apple users from V1 to staging')
    parser.add_argument('v1_url', help='V1 database URL')
    parser.add_argument('staging_url', help='Staging database URL')
    parser.add_argument('--validate', action='store_true', help='Run validation after migration')
    
    args = parser.parse_args()
    
    # Create logs directory
    Path('logs').mkdir(exist_ok=True)
    Path('backups').mkdir(exist_ok=True)
    
    # Run migration
    migration = SimpleMigration(args.v1_url, args.staging_url)
    success = migration.run_migration()
    
    if success and args.validate:
        migration.validate_migration()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
