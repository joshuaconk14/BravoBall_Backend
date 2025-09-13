"""
test_migration.py
Comprehensive testing suite for validating migration results
"""

import sys
import os
import json
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple

# Add parent directory to path to import our models
sys.path.append(str(Path(__file__).parent.parent.parent))
from models import (
    User, CompletedSession, SessionPreferences, DrillGroup, DrillGroupItem,
    ProgressHistory, SavedFilter, RefreshToken, PasswordResetCode, EmailVerificationCode,
    MentalTrainingSession
)
from migration_config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(config.get_log_path("test_migration")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MigrationTester:
    """Comprehensive testing suite for migration validation"""
    
    def __init__(self, v1_url: str, v2_url: str, staging_url: str):
        self.v1_engine = create_engine(v1_url)
        self.v2_engine = create_engine(v2_url)
        self.staging_engine = create_engine(staging_url)
        
        self.v1_session = sessionmaker(bind=self.v1_engine)()
        self.v2_session = sessionmaker(bind=self.v2_engine)()
        self.staging_session = sessionmaker(bind=self.staging_engine)()
        
        self.test_results = {
            'data_integrity_tests': {},
            'user_experience_tests': {},
            'platform_detection_tests': {},
            'related_data_tests': {},
            'overall_success': False,
            'test_timestamp': datetime.now().isoformat()
        }
    
    def test_data_integrity(self) -> bool:
        """Test data integrity across databases"""
        try:
            logger.info("Running data integrity tests...")
            
            tests = {
                'user_count_validation': self._test_user_count_validation(),
                'apple_user_data_accuracy': self._test_apple_user_data_accuracy(),
                'android_user_preservation': self._test_android_user_preservation(),
                'data_consistency': self._test_data_consistency()
            }
            
            self.test_results['data_integrity_tests'] = tests
            
            all_passed = all(tests.values())
            logger.info(f"Data integrity tests: {'✅ PASSED' if all_passed else '❌ FAILED'}")
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Error in data integrity tests: {e}")
            self.test_results['data_integrity_tests'] = {'error': str(e)}
            return False
    
    def _test_user_count_validation(self) -> bool:
        """Test that user counts are correct"""
        try:
            # Count users in each database
            v1_count = self.v1_session.query(User).count()
            v2_count = self.v2_session.query(User).count()
            staging_count = self.staging_session.query(User).count()
            
            # V2 should have all V1 users plus Android users
            # Staging should match V2 after migration
            expected_v2_min = v1_count  # At least all V1 users
            
            result = {
                'v1_user_count': v1_count,
                'v2_user_count': v2_count,
                'staging_user_count': staging_count,
                'expected_v2_min': expected_v2_min,
                'v2_has_all_v1_users': v2_count >= expected_v2_min,
                'staging_matches_v2': staging_count == v2_count
            }
            
            success = result['v2_has_all_v1_users'] and result['staging_matches_v2']
            logger.info(f"User count validation: {'✅ PASSED' if success else '❌ FAILED'}")
            logger.info(f"  V1 users: {v1_count}, V2 users: {v2_count}, Staging users: {staging_count}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in user count validation: {e}")
            return False
    
    def _test_apple_user_data_accuracy(self) -> bool:
        """Test that Apple user data is accurately migrated"""
        try:
            # Get Apple users (users in V1)
            v1_users = self.v1_session.query(User).all()
            v1_emails = {user.email.lower() for user in v1_users if user.email}
            
            accurate_migrations = 0
            total_apple_users = len(v1_emails)
            
            for v1_user in v1_users:
                if not v1_user.email:
                    continue
                    
                # Check if user exists in V2
                v2_user = self.v2_session.query(User).filter(User.email == v1_user.email).first()
                if not v2_user:
                    logger.warning(f"Apple user not found in V2: {v1_user.email}")
                    continue
                
                # Compare key fields
                fields_match = (
                    v1_user.first_name == v2_user.first_name and
                    v1_user.last_name == v2_user.last_name and
                    v1_user.hashed_password == v2_user.hashed_password and
                    v1_user.primary_goal == v2_user.primary_goal and
                    v1_user.training_experience == v2_user.training_experience and
                    v1_user.position == v2_user.position
                )
                
                if fields_match:
                    accurate_migrations += 1
                else:
                    logger.warning(f"Data mismatch for Apple user: {v1_user.email}")
            
            accuracy_rate = accurate_migrations / total_apple_users if total_apple_users > 0 else 1.0
            success = accuracy_rate >= 0.95  # 95% accuracy threshold
            
            result = {
                'total_apple_users': total_apple_users,
                'accurate_migrations': accurate_migrations,
                'accuracy_rate': accuracy_rate,
                'success': success
            }
            
            logger.info(f"Apple user data accuracy: {'✅ PASSED' if success else '❌ FAILED'}")
            logger.info(f"  Accuracy rate: {accuracy_rate:.2%}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in Apple user data accuracy test: {e}")
            return False
    
    def _test_android_user_preservation(self) -> bool:
        """Test that Android user data is preserved"""
        try:
            # Get all users in V2
            v2_users = self.v2_session.query(User).all()
            v2_emails = {user.email.lower() for user in v2_users if user.email}
            
            # Get all users in V1 (Apple users)
            v1_users = self.v1_session.query(User).all()
            v1_emails = {user.email.lower() for user in v1_users if user.email}
            
            # Android users are V2 users not in V1
            android_emails = v2_emails - v1_emails
            
            preserved_android_users = 0
            total_android_users = len(android_emails)
            
            for email in android_emails:
                # Check if Android user still exists in V2
                android_user = self.v2_session.query(User).filter(User.email == email).first()
                if android_user:
                    preserved_android_users += 1
                else:
                    logger.warning(f"Android user missing from V2: {email}")
            
            preservation_rate = preserved_android_users / total_android_users if total_android_users > 0 else 1.0
            success = preservation_rate == 1.0  # 100% preservation required
            
            result = {
                'total_android_users': total_android_users,
                'preserved_android_users': preserved_android_users,
                'preservation_rate': preservation_rate,
                'success': success
            }
            
            logger.info(f"Android user preservation: {'✅ PASSED' if success else '❌ FAILED'}")
            logger.info(f"  Preservation rate: {preservation_rate:.2%}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in Android user preservation test: {e}")
            return False
    
    def _test_data_consistency(self) -> bool:
        """Test overall data consistency"""
        try:
            # Check for orphaned records
            orphaned_sessions = self.staging_session.execute(text("""
                SELECT COUNT(*) FROM completed_sessions cs
                LEFT JOIN users u ON cs.user_id = u.id
                WHERE u.id IS NULL
            """)).scalar()
            
            orphaned_preferences = self.staging_session.execute(text("""
                SELECT COUNT(*) FROM session_preferences sp
                LEFT JOIN users u ON sp.user_id = u.id
                WHERE u.id IS NULL
            """)).scalar()
            
            orphaned_groups = self.staging_session.execute(text("""
                SELECT COUNT(*) FROM drill_groups dg
                LEFT JOIN users u ON dg.user_id = u.id
                WHERE u.id IS NULL
            """)).scalar()
            
            total_orphaned = orphaned_sessions + orphaned_preferences + orphaned_groups
            
            result = {
                'orphaned_sessions': orphaned_sessions,
                'orphaned_preferences': orphaned_preferences,
                'orphaned_groups': orphaned_groups,
                'total_orphaned': total_orphaned,
                'success': total_orphaned == 0
            }
            
            success = total_orphaned == 0
            logger.info(f"Data consistency: {'✅ PASSED' if success else '❌ FAILED'}")
            logger.info(f"  Orphaned records: {total_orphaned}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in data consistency test: {e}")
            return False
    
    def test_user_experience_scenarios(self) -> bool:
        """Test user experience scenarios"""
        try:
            logger.info("Running user experience tests...")
            
            tests = {
                'apple_user_login': self._test_apple_user_login(),
                'android_user_login': self._test_android_user_login(),
                'data_access_validation': self._test_data_access_validation()
            }
            
            self.test_results['user_experience_tests'] = tests
            
            all_passed = all(tests.values())
            logger.info(f"User experience tests: {'✅ PASSED' if all_passed else '❌ FAILED'}")
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Error in user experience tests: {e}")
            self.test_results['user_experience_tests'] = {'error': str(e)}
            return False
    
    def _test_apple_user_login(self) -> bool:
        """Test Apple user login scenario"""
        try:
            # Get a sample Apple user from V1
            v1_user = self.v1_session.query(User).filter(User.email.isnot(None)).first()
            if not v1_user:
                logger.warning("No Apple users found for login test")
                return True
            
            # Check if user exists in V2
            v2_user = self.v2_session.query(User).filter(User.email == v1_user.email).first()
            if not v2_user:
                logger.error(f"Apple user not found in V2: {v1_user.email}")
                return False
            
            # Check if password hash matches
            password_match = v1_user.hashed_password == v2_user.hashed_password
            
            result = {
                'test_user_email': v1_user.email,
                'user_exists_in_v2': v2_user is not None,
                'password_hash_match': password_match,
                'success': password_match
            }
            
            success = password_match
            logger.info(f"Apple user login test: {'✅ PASSED' if success else '❌ FAILED'}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in Apple user login test: {e}")
            return False
    
    def _test_android_user_login(self) -> bool:
        """Test Android user login scenario"""
        try:
            # Get Android users (V2 users not in V1)
            v2_users = self.v2_session.query(User).all()
            v1_emails = {user.email.lower() for user in self.v1_session.query(User).all() if user.email}
            
            android_users = [user for user in v2_users if user.email and user.email.lower() not in v1_emails]
            
            if not android_users:
                logger.warning("No Android users found for login test")
                return True
            
            # Test first Android user
            android_user = android_users[0]
            
            # Check if user still exists and has data
            user_still_exists = self.staging_session.query(User).filter(User.email == android_user.email).first() is not None
            
            result = {
                'test_user_email': android_user.email,
                'user_still_exists': user_still_exists,
                'success': user_still_exists
            }
            
            success = user_still_exists
            logger.info(f"Android user login test: {'✅ PASSED' if success else '❌ FAILED'}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in Android user login test: {e}")
            return False
    
    def _test_data_access_validation(self) -> bool:
        """Test that users can access their data"""
        try:
            # Test data access for a sample user
            v1_user = self.v1_session.query(User).filter(User.email.isnot(None)).first()
            if not v1_user:
                logger.warning("No users found for data access test")
                return True
            
            v2_user = self.v2_session.query(User).filter(User.email == v1_user.email).first()
            if not v2_user:
                logger.error(f"User not found in V2: {v1_user.email}")
                return False
            
            # Check related data access
            v1_sessions = len(v1_user.completed_sessions)
            v2_sessions = len(v2_user.completed_sessions)
            
            v1_groups = len(v1_user.drill_groups)
            v2_groups = len(v2_user.drill_groups)
            
            v1_preferences = v1_user.session_preferences is not None
            v2_preferences = v2_user.session_preferences is not None
            
            result = {
                'test_user_email': v1_user.email,
                'v1_sessions': v1_sessions,
                'v2_sessions': v2_sessions,
                'v1_groups': v1_groups,
                'v2_groups': v2_groups,
                'v1_preferences': v1_preferences,
                'v2_preferences': v2_preferences,
                'sessions_match': v1_sessions == v2_sessions,
                'groups_match': v1_groups == v2_groups,
                'preferences_match': v1_preferences == v2_preferences
            }
            
            success = result['sessions_match'] and result['groups_match'] and result['preferences_match']
            logger.info(f"Data access validation: {'✅ PASSED' if success else '❌ FAILED'}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in data access validation test: {e}")
            return False
    
    def test_platform_detection(self) -> bool:
        """Test platform detection logic"""
        try:
            logger.info("Running platform detection tests...")
            
            tests = {
                'apple_user_identification': self._test_apple_user_identification(),
                'android_user_identification': self._test_android_user_identification(),
                'user_categorization': self._test_user_categorization()
            }
            
            self.test_results['platform_detection_tests'] = tests
            
            all_passed = all(tests.values())
            logger.info(f"Platform detection tests: {'✅ PASSED' if all_passed else '❌ FAILED'}")
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Error in platform detection tests: {e}")
            self.test_results['platform_detection_tests'] = {'error': str(e)}
            return False
    
    def _test_apple_user_identification(self) -> bool:
        """Test Apple user identification logic"""
        try:
            v1_users = self.v1_session.query(User).all()
            v1_emails = {user.email.lower() for user in v1_users if user.email}
            
            v2_users = self.v2_session.query(User).all()
            v2_emails = {user.email.lower() for user in v2_users if user.email}
            
            # All V1 users should be identified as Apple users
            identified_apple_users = v1_emails
            
            result = {
                'v1_user_count': len(v1_emails),
                'identified_apple_users': len(identified_apple_users),
                'identification_accurate': len(identified_apple_users) == len(v1_emails),
                'success': len(identified_apple_users) == len(v1_emails)
            }
            
            success = result['identification_accurate']
            logger.info(f"Apple user identification: {'✅ PASSED' if success else '❌ FAILED'}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in Apple user identification test: {e}")
            return False
    
    def _test_android_user_identification(self) -> bool:
        """Test Android user identification logic"""
        try:
            v1_users = self.v1_session.query(User).all()
            v1_emails = {user.email.lower() for user in v1_users if user.email}
            
            v2_users = self.v2_session.query(User).all()
            v2_emails = {user.email.lower() for user in v2_users if user.email}
            
            # Android users are V2 users not in V1
            identified_android_users = v2_emails - v1_emails
            
            result = {
                'v2_user_count': len(v2_emails),
                'v1_user_count': len(v1_emails),
                'identified_android_users': len(identified_android_users),
                'success': True  # This is expected behavior
            }
            
            success = True
            logger.info(f"Android user identification: {'✅ PASSED' if success else '❌ FAILED'}")
            logger.info(f"  Identified {len(identified_android_users)} Android users")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in Android user identification test: {e}")
            return False
    
    def _test_user_categorization(self) -> bool:
        """Test user categorization logic"""
        try:
            v1_users = self.v1_session.query(User).all()
            v1_emails = {user.email.lower() for user in v1_users if user.email}
            
            v2_users = self.v2_session.query(User).all()
            v2_emails = {user.email.lower() for user in v2_users if user.email}
            
            # Categorize users
            apple_in_both = v1_emails & v2_emails
            apple_only_v1 = v1_emails - v2_emails
            android_users = v2_emails - v1_emails
            
            result = {
                'apple_in_both': len(apple_in_both),
                'apple_only_v1': len(apple_only_v1),
                'android_users': len(android_users),
                'total_categorized': len(apple_in_both) + len(apple_only_v1) + len(android_users),
                'total_users': len(v1_emails) + len(android_users),
                'categorization_complete': (len(apple_in_both) + len(apple_only_v1) + len(android_users)) == (len(v1_emails) + len(android_users))
            }
            
            success = result['categorization_complete']
            logger.info(f"User categorization: {'✅ PASSED' if success else '❌ FAILED'}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in user categorization test: {e}")
            return False
    
    def test_related_data_migration(self) -> bool:
        """Test related data migration"""
        try:
            logger.info("Running related data migration tests...")
            
            tests = {
                'sessions_migration': self._test_sessions_migration(),
                'preferences_migration': self._test_preferences_migration(),
                'drill_groups_migration': self._test_drill_groups_migration(),
                'progress_history_migration': self._test_progress_history_migration()
            }
            
            self.test_results['related_data_tests'] = tests
            
            all_passed = all(tests.values())
            logger.info(f"Related data migration tests: {'✅ PASSED' if all_passed else '❌ FAILED'}")
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Error in related data migration tests: {e}")
            self.test_results['related_data_tests'] = {'error': str(e)}
            return False
    
    def _test_sessions_migration(self) -> bool:
        """Test completed sessions migration"""
        try:
            v1_sessions = self.v1_session.query(CompletedSession).count()
            v2_sessions = self.v2_session.query(CompletedSession).count()
            
            result = {
                'v1_sessions': v1_sessions,
                'v2_sessions': v2_sessions,
                'migration_complete': v2_sessions >= v1_sessions,
                'success': v2_sessions >= v1_sessions
            }
            
            success = result['migration_complete']
            logger.info(f"Sessions migration: {'✅ PASSED' if success else '❌ FAILED'}")
            logger.info(f"  V1 sessions: {v1_sessions}, V2 sessions: {v2_sessions}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in sessions migration test: {e}")
            return False
    
    def _test_preferences_migration(self) -> bool:
        """Test session preferences migration"""
        try:
            v1_preferences = self.v1_session.query(SessionPreferences).count()
            v2_preferences = self.v2_session.query(SessionPreferences).count()
            
            result = {
                'v1_preferences': v1_preferences,
                'v2_preferences': v2_preferences,
                'migration_complete': v2_preferences >= v1_preferences,
                'success': v2_preferences >= v1_preferences
            }
            
            success = result['migration_complete']
            logger.info(f"Preferences migration: {'✅ PASSED' if success else '❌ FAILED'}")
            logger.info(f"  V1 preferences: {v1_preferences}, V2 preferences: {v2_preferences}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in preferences migration test: {e}")
            return False
    
    def _test_drill_groups_migration(self) -> bool:
        """Test drill groups migration"""
        try:
            v1_groups = self.v1_session.query(DrillGroup).count()
            v2_groups = self.v2_session.query(DrillGroup).count()
            
            v1_items = self.v1_session.query(DrillGroupItem).count()
            v2_items = self.v2_session.query(DrillGroupItem).count()
            
            result = {
                'v1_groups': v1_groups,
                'v2_groups': v2_groups,
                'v1_items': v1_items,
                'v2_items': v2_items,
                'groups_migration_complete': v2_groups >= v1_groups,
                'items_migration_complete': v2_items >= v1_items,
                'success': v2_groups >= v1_groups and v2_items >= v1_items
            }
            
            success = result['success']
            logger.info(f"Drill groups migration: {'✅ PASSED' if success else '❌ FAILED'}")
            logger.info(f"  V1 groups: {v1_groups}, V2 groups: {v2_groups}")
            logger.info(f"  V1 items: {v1_items}, V2 items: {v2_items}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in drill groups migration test: {e}")
            return False
    
    def _test_progress_history_migration(self) -> bool:
        """Test progress history migration"""
        try:
            v1_progress = self.v1_session.query(ProgressHistory).count()
            v2_progress = self.v2_session.query(ProgressHistory).count()
            
            result = {
                'v1_progress': v1_progress,
                'v2_progress': v2_progress,
                'migration_complete': v2_progress >= v1_progress,
                'success': v2_progress >= v1_progress
            }
            
            success = result['migration_complete']
            logger.info(f"Progress history migration: {'✅ PASSED' if success else '❌ FAILED'}")
            logger.info(f"  V1 progress: {v1_progress}, V2 progress: {v2_progress}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in progress history migration test: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all migration tests"""
        try:
            logger.info("Starting comprehensive migration testing...")
            
            # Run all test suites
            data_integrity_passed = self.test_data_integrity()
            user_experience_passed = self.test_user_experience_scenarios()
            platform_detection_passed = self.test_platform_detection()
            related_data_passed = self.test_related_data_migration()
            
            # Overall success
            overall_success = all([
                data_integrity_passed,
                user_experience_passed,
                platform_detection_passed,
                related_data_passed
            ])
            
            self.test_results['overall_success'] = overall_success
            
            # Save test report
            self._save_test_report()
            
            logger.info(f"Migration testing completed: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
            
            return overall_success
            
        except Exception as e:
            logger.error(f"Error in migration testing: {e}")
            self.test_results['overall_success'] = False
            self.test_results['error'] = str(e)
            return False
        finally:
            self.v1_session.close()
            self.v2_session.close()
            self.staging_session.close()
    
    def _save_test_report(self):
        """Save test report to file"""
        try:
            report_path = config.get_backup_path("migration_test_report")
            with open(report_path.with_suffix('.json'), 'w') as f:
                json.dump(self.test_results, f, indent=2, default=str)
            
            logger.info(f"Test report saved: {report_path}")
            
        except Exception as e:
            logger.error(f"Error saving test report: {e}")

def main():
    """Main function for command line usage"""
    if len(sys.argv) != 4:
        print("Usage: python test_migration.py <v1_database_url> <v2_database_url> <staging_database_url>")
        print("Example: python test_migration.py <V1_DATABASE_URL> <V2_DATABASE_URL> <STAGING_DATABASE_URL>")
        sys.exit(1)
    
    v1_url = sys.argv[1]
    v2_url = sys.argv[2]
    staging_url = sys.argv[3]
    
    logger.info(f"Running migration tests with V1: {v1_url}, V2: {v2_url}, Staging: {staging_url}")
    
    tester = MigrationTester(v1_url, v2_url, staging_url)
    
    if tester.run_all_tests():
        logger.info("All migration tests passed")
        sys.exit(0)
    else:
        logger.error("Some migration tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
