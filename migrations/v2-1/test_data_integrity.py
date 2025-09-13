#!/usr/bin/env python3
"""
test_data_integrity.py
Comprehensive data integrity testing for V2 migration
Tests that migrated data from V1 matches the target database (V2 or Staging)
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent))

from models_v1 import UserV1, CompletedSessionV1, SessionPreferencesV1, DrillGroupV1, ProgressHistoryV1
from models import User, CompletedSession, SessionPreferences, DrillGroup, ProgressHistory, RefreshToken, PasswordResetCode
from migration_config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(f'logs/data_integrity_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataIntegrityTester:
    """Comprehensive data integrity testing for migration"""
    
    def __init__(self, v1_url: str, v2_url: str, staging_url: str = None):
        self.v1_url = v1_url
        self.v2_url = v2_url
        self.staging_url = staging_url
        
        # Determine which database to test against
        self.is_testing_mode = config.is_debug_mode()
        
        if self.is_testing_mode and staging_url:
            self.target_url = staging_url
            self.target_name = "Staging"
            logger.info("🧪 Testing mode: Using STAGING database for validation")
        else:
            self.target_url = v2_url
            self.target_name = "V2"
            logger.info("🚀 Production mode: Using V2 database for validation")
        
        # Create database connections
        self.v1_engine = create_engine(v1_url)
        self.target_engine = create_engine(self.target_url)
        self.v1_session = sessionmaker(bind=self.v1_engine)()
        self.target_session = sessionmaker(bind=self.target_engine)()
        
        self.test_results = {
            'test_config': {
                'testing_mode': self.is_testing_mode,
                'target_database': self.target_name,
                'v1_url': v1_url,
                'target_url': self.target_url
            },
            'user_data_accuracy': [],
            'session_data_accuracy': [],
            'preference_data_accuracy': [],
            'drill_group_data_accuracy': [],
            'progress_data_accuracy': [],
            'relationship_integrity': [],
            'authentication_data': [],
            'errors': [],
            'summary': {}
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all data integrity tests"""
        logger.info(f"🧪 Starting comprehensive data integrity testing...")
        logger.info(f"📊 Testing V1 → {self.target_name} data migration accuracy")
        
        try:
            # Test 1: User Data Accuracy
            self.test_user_data_accuracy()
            
            # Test 2: Session Data Accuracy
            self.test_session_data_accuracy()
            
            # Test 3: Preference Data Accuracy
            self.test_preference_data_accuracy()
            
            # Test 4: Drill Group Data Accuracy
            self.test_drill_group_data_accuracy()
            
            # Test 5: Progress Data Accuracy
            self.test_progress_data_accuracy()
            
            # Test 6: Relationship Integrity
            self.test_relationship_integrity()
            
            # Test 7: Authentication Data
            self.test_authentication_data()
            
            # Generate summary
            self.generate_summary()
            
            logger.info(f"✅ Data integrity testing completed for {self.target_name}")
            return self.test_results
            
        except Exception as e:
            logger.error(f"❌ Data integrity testing failed: {e}")
            self.test_results['errors'].append(f"Testing failed: {e}")
            return self.test_results
    
    def test_user_data_accuracy(self):
        """Test user profile data accuracy"""
        logger.info("🔍 Testing user data accuracy...")
        
        try:
            # Get sample users from both databases
            v1_users = self.v1_session.query(UserV1).limit(100).all()
            target_users = self.target_session.query(User).limit(100).all()
            
            for v1_user in v1_users:
                target_user = self.target_session.query(User).filter(User.email == v1_user.email).first()
                
                if target_user:
                    # Compare user data
                    user_test = {
                        'email': v1_user.email,
                        'tests': {
                            'first_name': v1_user.first_name == target_user.first_name,
                            'last_name': v1_user.last_name == target_user.last_name,
                            'primary_goal': v1_user.primary_goal == target_user.primary_goal,
                            'biggest_challenge': v1_user.biggest_challenge == target_user.biggest_challenge,
                            'training_experience': v1_user.training_experience == target_user.training_experience,
                            'position': v1_user.position == target_user.position,
                            'age_range': v1_user.age_range == target_user.age_range,
                            'strengths': v1_user.strengths == target_user.strengths,
                            'areas_to_improve': v1_user.areas_to_improve == target_user.areas_to_improve,
                            'training_location': v1_user.training_location == target_user.training_location,
                            'available_equipment': v1_user.available_equipment == target_user.available_equipment,
                            'daily_training_time': v1_user.daily_training_time == target_user.daily_training_time,
                            'weekly_training_days': v1_user.weekly_training_days == target_user.weekly_training_days,
                            'playstyle': v1_user.playstyle == target_user.playstyle
                        }
                    }
                    
                    # Calculate accuracy percentage
                    passed_tests = sum(1 for test in user_test['tests'].values() if test)
                    total_tests = len(user_test['tests'])
                    accuracy = (passed_tests / total_tests) * 100
                    
                    user_test['accuracy'] = accuracy
                    user_test['passed_tests'] = passed_tests
                    user_test['total_tests'] = total_tests
                    
                    self.test_results['user_data_accuracy'].append(user_test)
                    
                    if accuracy < 100:
                        logger.warning(f"⚠️ User {v1_user.email} has {accuracy:.1f}% data accuracy")
                    else:
                        logger.info(f"✅ User {v1_user.email} has 100% data accuracy")
                else:
                    logger.warning(f"⚠️ User {v1_user.email} not found in {self.target_name}")
                    self.test_results['user_data_accuracy'].append({
                        'email': v1_user.email,
                        'error': f'User not found in {self.target_name}',
                        'accuracy': 0
                    })
                    
        except Exception as e:
            logger.error(f"❌ User data accuracy test failed: {e}")
            self.test_results['errors'].append(f"User data accuracy test failed: {e}")
    
    def test_session_data_accuracy(self):
        """Test completed session data accuracy"""
        logger.info("🔍 Testing session data accuracy...")
        
        try:
            # Get sample sessions from both databases
            v1_sessions = self.v1_session.query(CompletedSessionV1).limit(50).all()
            
            for v1_session in v1_sessions:
                # Find corresponding user in V2
                v2_user = self.target_session.query(User).filter(User.email == v1_session.user.email).first()
                
                if v2_user:
                    # Find corresponding session in V2
                    v2_session = self.target_session.query(CompletedSession).filter(
                        CompletedSession.user_id == v2_user.id,
                        CompletedSession.date == v1_session.date
                    ).first()
                    
                    if v2_session:
                        # Compare session data
                        session_test = {
                            'user_email': v1_session.user.email,
                            'date': str(v1_session.date),
                            'tests': {
                                'session_type': getattr(v1_session, 'session_type', 'drill_training') == v2_session.session_type,
                                'total_completed_drills': v1_session.total_completed_drills == v2_session.total_completed_drills,
                                'total_drills': v1_session.total_drills == v2_session.total_drills,
                                'drills': v1_session.drills == v2_session.drills,
                                'duration_minutes': getattr(v1_session, 'duration_minutes', 0) == v2_session.duration_minutes,
                                'notes': getattr(v1_session, 'notes', '') == v2_session.notes
                            }
                        }
                        
                        # Calculate accuracy
                        passed_tests = sum(1 for test in session_test['tests'].values() if test)
                        total_tests = len(session_test['tests'])
                        accuracy = (passed_tests / total_tests) * 100
                        
                        session_test['accuracy'] = accuracy
                        session_test['passed_tests'] = passed_tests
                        session_test['total_tests'] = total_tests
                        
                        self.test_results['session_data_accuracy'].append(session_test)
                        
                        if accuracy < 100:
                            logger.warning(f"⚠️ Session for {v1_session.user.email} on {v1_session.date} has {accuracy:.1f}% accuracy")
                        else:
                            logger.info(f"✅ Session for {v1_session.user.email} on {v1_session.date} has 100% accuracy")
                    else:
                        logger.warning(f"⚠️ Session for {v1_session.user.email} on {v1_session.date} not found in {self.target_name}")
                        self.test_results['session_data_accuracy'].append({
                            'user_email': v1_session.user.email,
                            'date': str(v1_session.date),
                            'error': f'Session not found in {self.target_name}',
                            'accuracy': 0
                        })
                        
        except Exception as e:
            logger.error(f"❌ Session data accuracy test failed: {e}")
            self.test_results['errors'].append(f"Session data accuracy test failed: {e}")
    
    def test_preference_data_accuracy(self):
        """Test session preference data accuracy"""
        logger.info("🔍 Testing preference data accuracy...")
        
        try:
            # Get sample preferences from both databases
            v1_preferences = self.v1_session.query(SessionPreferencesV1).limit(50).all()
            
            for v1_pref in v1_preferences:
                # Find corresponding user in V2
                v2_user = self.target_session.query(User).filter(User.email == v1_pref.user.email).first()
                
                if v2_user:
                    # Find corresponding preference in V2
                    v2_pref = self.target_session.query(SessionPreferences).filter(
                        SessionPreferences.user_id == v2_user.id
                    ).first()
                    
                    if v2_pref:
                        # Compare preference data
                        pref_test = {
                            'user_email': v1_pref.user.email,
                            'tests': {
                                'difficulty': v1_pref.difficulty == v2_pref.difficulty,
                                'duration': v1_pref.duration == v2_pref.duration,
                                'focus_areas': v1_pref.focus_areas == v2_pref.focus_areas,
                                'equipment': v1_pref.equipment == v2_pref.equipment,
                                'location': v1_pref.location == v2_pref.location,
                                'training_style': v1_pref.training_style == v2_pref.training_style
                            }
                        }
                        
                        # Calculate accuracy
                        passed_tests = sum(1 for test in pref_test['tests'].values() if test)
                        total_tests = len(pref_test['tests'])
                        accuracy = (passed_tests / total_tests) * 100
                        
                        pref_test['accuracy'] = accuracy
                        pref_test['passed_tests'] = passed_tests
                        pref_test['total_tests'] = total_tests
                        
                        self.test_results['preference_data_accuracy'].append(pref_test)
                        
                        if accuracy < 100:
                            logger.warning(f"⚠️ Preferences for {v1_pref.user.email} have {accuracy:.1f}% accuracy")
                        else:
                            logger.info(f"✅ Preferences for {v1_pref.user.email} have 100% accuracy")
                    else:
                        logger.warning(f"⚠️ Preferences for {v1_pref.user.email} not found in V2")
                        self.test_results['preference_data_accuracy'].append({
                            'user_email': v1_pref.user.email,
                            'error': 'Preferences not found in V2',
                            'accuracy': 0
                        })
                        
        except Exception as e:
            logger.error(f"❌ Preference data accuracy test failed: {e}")
            self.test_results['errors'].append(f"Preference data accuracy test failed: {e}")
    
    def test_drill_group_data_accuracy(self):
        """Test drill group data accuracy"""
        logger.info("🔍 Testing drill group data accuracy...")
        
        try:
            # Get sample drill groups from both databases
            v1_groups = self.v1_session.query(DrillGroupV1).limit(50).all()
            
            for v1_group in v1_groups:
                # Find corresponding user in V2
                v2_user = self.target_session.query(User).filter(User.email == v1_group.user.email).first()
                
                if v2_user:
                    # Find corresponding drill group in V2
                    v2_group = self.target_session.query(DrillGroup).filter(
                        DrillGroup.user_id == v2_user.id,
                        DrillGroup.name == v1_group.name
                    ).first()
                    
                    if v2_group:
                        # Compare drill group data
                        group_test = {
                            'user_email': v1_group.user.email,
                            'group_name': v1_group.name,
                            'tests': {
                                'name': v1_group.name == v2_group.name,
                                'description': v1_group.description == v2_group.description,
                                'is_liked_group': v1_group.is_liked_group == v2_group.is_liked_group
                            }
                        }
                        
                        # Calculate accuracy
                        passed_tests = sum(1 for test in group_test['tests'].values() if test)
                        total_tests = len(group_test['tests'])
                        accuracy = (passed_tests / total_tests) * 100
                        
                        group_test['accuracy'] = accuracy
                        group_test['passed_tests'] = passed_tests
                        group_test['total_tests'] = total_tests
                        
                        self.test_results['drill_group_data_accuracy'].append(group_test)
                        
                        if accuracy < 100:
                            logger.warning(f"⚠️ Drill group '{v1_group.name}' for {v1_group.user.email} has {accuracy:.1f}% accuracy")
                        else:
                            logger.info(f"✅ Drill group '{v1_group.name}' for {v1_group.user.email} has 100% accuracy")
                    else:
                        logger.warning(f"⚠️ Drill group '{v1_group.name}' for {v1_group.user.email} not found in V2")
                        self.test_results['drill_group_data_accuracy'].append({
                            'user_email': v1_group.user.email,
                            'group_name': v1_group.name,
                            'error': 'Drill group not found in V2',
                            'accuracy': 0
                        })
                        
        except Exception as e:
            logger.error(f"❌ Drill group data accuracy test failed: {e}")
            self.test_results['errors'].append(f"Drill group data accuracy test failed: {e}")
    
    def test_progress_data_accuracy(self):
        """Test progress history data accuracy"""
        logger.info("🔍 Testing progress data accuracy...")
        
        try:
            # Get sample progress records from both databases
            v1_progress = self.v1_session.query(ProgressHistoryV1).limit(50).all()
            
            for v1_prog in v1_progress:
                # Find corresponding user in V2
                v2_user = self.target_session.query(User).filter(User.email == v1_prog.user.email).first()
                
                if v2_user:
                    # Find corresponding progress record in V2
                    v2_prog = self.target_session.query(ProgressHistory).filter(
                        ProgressHistory.user_id == v2_user.id,
                        ProgressHistory.date == v1_prog.date
                    ).first()
                    
                    if v2_prog:
                        # Compare progress data
                        progress_test = {
                            'user_email': v1_prog.user.email,
                            'date': str(v1_prog.date),
                            'tests': {
                                'total_drills_completed': v1_prog.total_drills_completed == v2_prog.total_drills_completed,
                                'unique_drills_completed': v1_prog.unique_drills_completed == v2_prog.unique_drills_completed,
                                'total_time_all_sessions': v1_prog.total_time_all_sessions == v2_prog.total_time_all_sessions,
                                'completed_sessions_count': v1_prog.completed_sessions_count == v2_prog.completed_sessions_count,
                                'current_streak': v1_prog.current_streak == v2_prog.current_streak,
                                'highest_streak': v1_prog.highest_streak == v2_prog.highest_streak
                            }
                        }
                        
                        # Calculate accuracy
                        passed_tests = sum(1 for test in progress_test['tests'].values() if test)
                        total_tests = len(progress_test['tests'])
                        accuracy = (passed_tests / total_tests) * 100
                        
                        progress_test['accuracy'] = accuracy
                        progress_test['passed_tests'] = passed_tests
                        progress_test['total_tests'] = total_tests
                        
                        self.test_results['progress_data_accuracy'].append(progress_test)
                        
                        if accuracy < 100:
                            logger.warning(f"⚠️ Progress for {v1_prog.user.email} on {v1_prog.date} has {accuracy:.1f}% accuracy")
                        else:
                            logger.info(f"✅ Progress for {v1_prog.user.email} on {v1_prog.date} has 100% accuracy")
                    else:
                        logger.warning(f"⚠️ Progress for {v1_prog.user.email} on {v1_prog.date} not found in V2")
                        self.test_results['progress_data_accuracy'].append({
                            'user_email': v1_prog.user.email,
                            'date': str(v1_prog.date),
                            'error': 'Progress record not found in V2',
                            'accuracy': 0
                        })
                        
        except Exception as e:
            logger.error(f"❌ Progress data accuracy test failed: {e}")
            self.test_results['errors'].append(f"Progress data accuracy test failed: {e}")
    
    def test_relationship_integrity(self):
        """Test foreign key relationship integrity"""
        logger.info("🔍 Testing relationship integrity...")
        
        try:
            # Test user-session relationships
            orphaned_sessions = self.target_session.execute(text("""
                SELECT cs.id, cs.user_id 
                FROM completed_sessions cs 
                LEFT JOIN users u ON cs.user_id = u.id 
                WHERE u.id IS NULL
            """)).fetchall()
            
            if orphaned_sessions:
                logger.warning(f"⚠️ Found {len(orphaned_sessions)} orphaned sessions")
                self.test_results['relationship_integrity'].append({
                    'test': 'user-session relationships',
                    'status': 'failed',
                    'orphaned_count': len(orphaned_sessions)
                })
            else:
                logger.info("✅ All sessions have valid user relationships")
                self.test_results['relationship_integrity'].append({
                    'test': 'user-session relationships',
                    'status': 'passed',
                    'orphaned_count': 0
                })
            
            # Test user-preference relationships
            orphaned_preferences = self.target_session.execute(text("""
                SELECT sp.id, sp.user_id 
                FROM session_preferences sp 
                LEFT JOIN users u ON sp.user_id = u.id 
                WHERE u.id IS NULL
            """)).fetchall()
            
            if orphaned_preferences:
                logger.warning(f"⚠️ Found {len(orphaned_preferences)} orphaned preferences")
                self.test_results['relationship_integrity'].append({
                    'test': 'user-preference relationships',
                    'status': 'failed',
                    'orphaned_count': len(orphaned_preferences)
                })
            else:
                logger.info("✅ All preferences have valid user relationships")
                self.test_results['relationship_integrity'].append({
                    'test': 'user-preference relationships',
                    'status': 'passed',
                    'orphaned_count': 0
                })
            
            # Test user-drill group relationships
            orphaned_groups = self.target_session.execute(text("""
                SELECT dg.id, dg.user_id 
                FROM drill_groups dg 
                LEFT JOIN users u ON dg.user_id = u.id 
                WHERE u.id IS NULL
            """)).fetchall()
            
            if orphaned_groups:
                logger.warning(f"⚠️ Found {len(orphaned_groups)} orphaned drill groups")
                self.test_results['relationship_integrity'].append({
                    'test': 'user-drill group relationships',
                    'status': 'failed',
                    'orphaned_count': len(orphaned_groups)
                })
            else:
                logger.info("✅ All drill groups have valid user relationships")
                self.test_results['relationship_integrity'].append({
                    'test': 'user-drill group relationships',
                    'status': 'passed',
                    'orphaned_count': 0
                })
                
        except Exception as e:
            logger.error(f"❌ Relationship integrity test failed: {e}")
            self.test_results['errors'].append(f"Relationship integrity test failed: {e}")
    
    def test_authentication_data(self):
        """Test authentication data (passwords, tokens)"""
        logger.info("🔍 Testing authentication data...")
        
        try:
            # Test password hashes
            v1_users = self.v1_session.query(UserV1).limit(50).all()
            
            for v1_user in v1_users:
                v2_user = self.target_session.query(User).filter(User.email == v1_user.email).first()
                
                if v2_user:
                    # Compare password hashes
                    if v1_user.hashed_password == v2_user.hashed_password:
                        logger.info(f"✅ Password hash for {v1_user.email} is correct")
                        self.test_results['authentication_data'].append({
                            'user_email': v1_user.email,
                            'test': 'password_hash',
                            'status': 'passed'
                        })
                    else:
                        logger.warning(f"⚠️ Password hash for {v1_user.email} is incorrect")
                        self.test_results['authentication_data'].append({
                            'user_email': v1_user.email,
                            'test': 'password_hash',
                            'status': 'failed'
                        })
            
            # Test refresh tokens
            v2_tokens = self.target_session.query(RefreshToken).limit(50).all()
            
            for token in v2_tokens:
                user = self.target_session.query(User).filter(User.id == token.user_id).first()
                if user:
                    logger.info(f"✅ Refresh token for {user.email} has valid user relationship")
                    self.test_results['authentication_data'].append({
                        'user_email': user.email,
                        'test': 'refresh_token_relationship',
                        'status': 'passed'
                    })
                else:
                    logger.warning(f"⚠️ Refresh token has invalid user relationship")
                    self.test_results['authentication_data'].append({
                        'test': 'refresh_token_relationship',
                        'status': 'failed'
                    })
                    
        except Exception as e:
            logger.error(f"❌ Authentication data test failed: {e}")
            self.test_results['errors'].append(f"Authentication data test failed: {e}")
    
    def generate_summary(self):
        """Generate test summary"""
        logger.info("📊 Generating test summary...")
        
        summary = {
            'total_tests_run': 0,
            'total_tests_passed': 0,
            'total_tests_failed': 0,
            'overall_accuracy': 0,
            'test_categories': {}
        }
        
        # Calculate summary for each test category
        categories = [
            'user_data_accuracy',
            'session_data_accuracy', 
            'preference_data_accuracy',
            'drill_group_data_accuracy',
            'progress_data_accuracy'
        ]
        
        total_accuracy = 0
        category_count = 0
        
        for category in categories:
            if self.test_results[category]:
                category_summary = {
                    'total_tests': len(self.test_results[category]),
                    'passed_tests': 0,
                    'failed_tests': 0,
                    'average_accuracy': 0
                }
                
                total_accuracy_sum = 0
                for test in self.test_results[category]:
                    if 'accuracy' in test:
                        total_accuracy_sum += test['accuracy']
                        if test['accuracy'] == 100:
                            category_summary['passed_tests'] += 1
                        else:
                            category_summary['failed_tests'] += 1
                
                if category_summary['total_tests'] > 0:
                    category_summary['average_accuracy'] = total_accuracy_sum / category_summary['total_tests']
                    total_accuracy += category_summary['average_accuracy']
                    category_count += 1
                
                summary['test_categories'][category] = category_summary
                summary['total_tests_run'] += category_summary['total_tests']
                summary['total_tests_passed'] += category_summary['passed_tests']
                summary['total_tests_failed'] += category_summary['failed_tests']
        
        # Calculate overall accuracy
        if category_count > 0:
            summary['overall_accuracy'] = total_accuracy / category_count
        
        # Add relationship integrity summary
        if self.test_results['relationship_integrity']:
            relationship_passed = sum(1 for test in self.test_results['relationship_integrity'] if test['status'] == 'passed')
            relationship_total = len(self.test_results['relationship_integrity'])
            summary['test_categories']['relationship_integrity'] = {
                'total_tests': relationship_total,
                'passed_tests': relationship_passed,
                'failed_tests': relationship_total - relationship_passed,
                'average_accuracy': (relationship_passed / relationship_total) * 100 if relationship_total > 0 else 0
            }
        
        # Add authentication data summary
        if self.test_results['authentication_data']:
            auth_passed = sum(1 for test in self.test_results['authentication_data'] if test['status'] == 'passed')
            auth_total = len(self.test_results['authentication_data'])
            summary['test_categories']['authentication_data'] = {
                'total_tests': auth_total,
                'passed_tests': auth_passed,
                'failed_tests': auth_total - auth_passed,
                'average_accuracy': (auth_passed / auth_total) * 100 if auth_total > 0 else 0
            }
        
        summary['errors'] = len(self.test_results['errors'])
        
        self.test_results['summary'] = summary
        
        # Log summary
        logger.info("📊 Test Summary:")
        logger.info(f"  Overall Accuracy: {summary['overall_accuracy']:.1f}%")
        logger.info(f"  Total Tests: {summary['total_tests_run']}")
        logger.info(f"  Passed: {summary['total_tests_passed']}")
        logger.info(f"  Failed: {summary['total_tests_failed']}")
        logger.info(f"  Errors: {summary['errors']}")
        
        for category, cat_summary in summary['test_categories'].items():
            logger.info(f"  {category}: {cat_summary['average_accuracy']:.1f}% accuracy ({cat_summary['passed_tests']}/{cat_summary['total_tests']} passed)")
    
    def save_results(self, filename: str = None):
        """Save test results to file"""
        if filename is None:
            filename = f"backups/data_integrity_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        logger.info(f"💾 Test results saved to {filename}")
        return filename

def main():
    """Main function to run data integrity tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run data integrity tests for V2 migration')
    parser.add_argument('v1_url', help='V1 database URL')
    parser.add_argument('v2_url', help='V2 database URL')
    parser.add_argument('--staging-url', help='Staging database URL (optional, used in testing mode)')
    parser.add_argument('--output', help='Output file for results')
    
    args = parser.parse_args()
    
    # Run tests
    tester = DataIntegrityTester(args.v1_url, args.v2_url, args.staging_url)
    results = tester.run_all_tests()
    
    # Save results
    output_file = tester.save_results(args.output)
    
    # Print final summary
    summary = results['summary']
    print(f"\n🎯 Final Results:")
    print(f"  Overall Accuracy: {summary['overall_accuracy']:.1f}%")
    print(f"  Total Tests: {summary['total_tests_run']}")
    print(f"  Passed: {summary['total_tests_passed']}")
    print(f"  Failed: {summary['total_tests_failed']}")
    print(f"  Errors: {summary['errors']}")
    
    if summary['overall_accuracy'] >= 95:
        print("✅ Data integrity test PASSED")
        return 0
    else:
        print("❌ Data integrity test FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
