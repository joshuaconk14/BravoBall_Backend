"""
Unit tests for session generator. Run with `pytest unit_tests/session_generator.py -s`
"""

import sys
from pathlib import Path
import pytest
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session

sys.path.append(str(Path(__file__).parent.parent))

from models import *
from services.session_generator import SessionGenerator
from db import SessionLocal
from services.preference_service import PreferenceService
from models import SessionPreferences, TrainingStyle, Equipment, TrainingLocation, Difficulty

def create_test_user():
    """Create a test user with onboarding data"""
    return User(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        skill_level=ExperienceLevel.INTERMEDIATE.value
    )

def create_test_onboarding_data():
    """Create sample onboarding data"""
    return OnboardingData(
        primary_goal=PrimaryGoal.IMPROVE_SKILL,
        main_challenge=Challenge.LACK_OF_TIME,
        experience_level=ExperienceLevel.INTERMEDIATE,
        position=Position.DEFENSIVE_MID,
        playstyle_representative="Alan Virgilus",
        age_range=AgeRange.ADULT,
        strengths=[Skill.PASSING, Skill.DRIBBLING],
        areas_to_improve=[Skill.SHOOTING, Skill.FITNESS],
        training_location=TrainingLocation.FULL_FIELD,
        available_equipment=[Equipment.BALL, Equipment.CONES, Equipment.GOALS],
        daily_training_time=TrainingDuration.MINS_45,
        weekly_training_days=TrainingFrequency.MODERATE
    )

@pytest.mark.asyncio
async def test_session_generation():
    """Test that session generator creates appropriate training sessions"""
    db = SessionLocal()
    try:
        # Create test preferences
        preferences = SessionPreferences(
            duration=30,
            available_equipment=["BALL", "WALL", "CONES", "GOALS"],
            training_style=TrainingStyle.MEDIUM_INTENSITY,
            training_location=TrainingLocation.SMALL_FIELD.value,
            difficulty=Difficulty.BEGINNER,
            target_skills=["passing", "shooting"]
        )

        # Initialize session generator
        generator = SessionGenerator(db)
        
        # Generate a session
        session = await generator.generate_session(preferences)
        
        print("\nGenerated Session Details:")
        print(f"Total Duration: {session.total_duration} minutes")
        print("\nDrills in session:")
        for drill in session.drills:
            print(f"\n{'-'*40}")
            print(f"Drill: {drill.title}")
            print(f"Duration: {drill.adjusted_duration if hasattr(drill, 'adjusted_duration') else drill.duration} minutes")
            print(f"Equipment: {drill.required_equipment}")
            print(f"Difficulty: {drill.difficulty}")
            
        # Assertions
        assert session is not None, "Session should be generated"
        assert len(session.drills) > 0, "Session should contain drills"
        assert session.total_duration <= preferences.duration, "Session duration should not exceed preferred duration"
        
        # Check if drills match preferences
        for drill in session.drills:
            # Check equipment
            required_equipment = set(drill.required_equipment)
            available_equipment = set(preferences.available_equipment)
            assert required_equipment.issubset(available_equipment), \
                f"Drill {drill.title} requires equipment not available: {required_equipment - available_equipment}"
            
            # Check training location
            assert preferences.training_location in drill.suitable_locations, \
                f"Drill {drill.title} not suitable for location {preferences.training_location}"
            
            # Instead of checking exact difficulty match, ensure the drill has been properly adjusted
            assert hasattr(drill, 'intensity_modifier'), \
                f"Drill {drill.title} should have an intensity modifier"
            
            # Verify that harder drills for beginners have reduced intensity
            if drill.difficulty == 'intermediate' and preferences.difficulty == Difficulty.BEGINNER:
                assert drill.intensity_modifier < 1.0, \
                    f"Drill {drill.title} should have reduced intensity for beginner"
            # Verify that easier drills for advanced players have increased intensity
            elif drill.difficulty == 'beginner' and preferences.difficulty == Difficulty.ADVANCED:
                assert drill.intensity_modifier > 1.0, \
                    f"Drill {drill.title} should have increased intensity for advanced player"

    finally:
        db.close()

def test_session_generation_sync():
    """Test the session generator synchronously"""
    async def run_test():
        db = SessionLocal()
        try:
            # Clean up any existing test data first
            test_user = db.query(User).filter(User.email == "test@example.com").first()
            if test_user:
                db.query(SessionPreferences).filter(SessionPreferences.user_id == test_user.id).delete()
                db.query(User).filter(User.id == test_user.id).delete()
            db.commit()

            onboarding_data = create_test_onboarding_data()
            session_prefs = SessionPreferences(
                duration=45,
                available_equipment=[eq.value for eq in onboarding_data.available_equipment],
                training_style=TrainingStyle.MEDIUM_INTENSITY,
                training_location=TrainingLocation.FULL_FIELD.value,
                difficulty=Difficulty.INTERMEDIATE,
                target_skills=[skill.value for skill in onboarding_data.areas_to_improve]
            )
            
            generator = SessionGenerator(db)
            return await generator.generate_session(session_prefs)
        finally:
            db.close()
    
    session = asyncio.run(run_test())
    assert session.total_duration <= 45

if __name__ == "__main__":
    asyncio.run(test_session_generation()) 