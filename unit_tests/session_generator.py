"""
Simple test for session generator to verify basic functionality.
Run with `pytest unit_tests/session_generator.py -v -s`
"""

import sys
from pathlib import Path
import pytest
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from models import *
from services.session_generator import SessionGenerator
from db import SessionLocal

# Simplified test profiles
USER_PROFILES = {
    "beginner_player": {
        "name": "Beginner Player",
        "preferences": {
            "duration": 30,
            "available_equipment": [Equipment.BALL.value, Equipment.CONES.value],
            "training_style": TrainingStyle.MEDIUM_INTENSITY.value,
            "training_location": TrainingLocation.BACKYARD.value,
            "difficulty": Difficulty.BEGINNER.value,
            "target_skills": ["passing", "first_touch"]
        }
    },
    "limited_equipment_player": {
        "name": "Limited Equipment Player",
        "preferences": {
            "duration": 30,
            "available_equipment": [Equipment.BALL.value],
            "training_style": TrainingStyle.MEDIUM_INTENSITY.value,
            "training_location": TrainingLocation.SMALL_ROOM.value,
            "difficulty": Difficulty.INTERMEDIATE.value,
            "target_skills": ["ball_mastery", "first_touch"]
        }
    }
}

def create_session_preferences(profile):
    """Create SessionPreferences object from profile data"""
    return SessionPreferences(
        duration=profile["preferences"]["duration"],
        available_equipment=profile["preferences"]["available_equipment"],
        training_style=profile["preferences"]["training_style"],
        training_location=profile["preferences"]["training_location"],
        difficulty=profile["preferences"]["difficulty"],
        target_skills=profile["preferences"]["target_skills"]
    )

def print_session_details(profile_name, session, profile):
    """Print session information in a clean, formatted way"""
    print("\n" + "="*80)
    print(f"Testing Profile: {profile_name}")
    print("-"*80)
    
    # Print Profile Preferences
    print("\nProfile Preferences:")
    prefs = profile["preferences"]
    print(f"⏱  Duration Goal: {prefs['duration']} minutes")
    print(f"📍  Location: {prefs['training_location']}")
    print(f"🎯  Difficulty: {prefs['difficulty']}")
    print(f"⚽  Equipment: {', '.join(prefs['available_equipment'])}")
    print(f"🔄  Target Skills: {', '.join(prefs['target_skills'])}")
    
    # Print Drill Selection Process
    print("\nDrill Selection:")
    for drill in session.drills:
        print(f"\n🔸 {drill.title}")
        print(f"   {'Duration':12} │ Original: {drill.original_duration:2d} min │ Adjusted: {drill.adjusted_duration:2d} min")
        print(f"   {'Equipment':12} │ {', '.join(drill.required_equipment)}")
        print(f"   {'Difficulty':12} │ {drill.difficulty}")
        print(f"   {'Intensity':12} │ {drill.intensity_modifier:.2f}x")
    
    # Print Summary
    print("\nSession Summary:")
    print(f"✓ Total Duration: {session.total_duration}/{prefs['duration']} minutes")
    print(f"✓ Number of Drills: {len(session.drills)}")
    equipment_used = set()
    for drill in session.drills:
        equipment_used.update(drill.required_equipment)
    print(f"✓ Equipment Types Used: {len(equipment_used)}")
    print("="*80 + "\n")

@pytest.mark.asyncio
async def test_session_generation():
    """Test session generation for different user profiles"""
    db = SessionLocal()
    try:
        generator = SessionGenerator(db)
        
        for profile_name, profile in USER_PROFILES.items():
            # Create preferences from profile
            preferences = create_session_preferences(profile)
            
            # Generate session
            session = await generator.generate_session(preferences)
            
            # Print detailed session information
            print_session_details(profile_name, session, profile)
            
            # Basic assertions
            assert session is not None, f"Session should be generated for {profile_name}"
            assert len(session.drills) > 0, f"Session should contain drills for {profile_name}"
            assert session.total_duration <= preferences.duration, \
                f"Session duration ({session.total_duration}) should not exceed preferred duration ({preferences.duration})"
            
    finally:
        db.close()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 