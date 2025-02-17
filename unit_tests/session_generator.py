"""
Unit tests for session generator focusing on different user profiles.
Run with `pytest unit_tests/session_generator.py -v -s`
"""

import sys
from pathlib import Path
import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any

sys.path.append(str(Path(__file__).parent.parent))

from models import *
from services.session_generator import SessionGenerator
from db import SessionLocal

# Test User Profiles
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
        },
        "description": "New player with basic equipment, training at home"
    },
    
    "intermediate_player": {
        "name": "Intermediate Player",
        "preferences": {
            "duration": 45,
            "available_equipment": [Equipment.BALL.value, Equipment.CONES.value, Equipment.GOALS.value],
            "training_style": TrainingStyle.HIGH_INTENSITY.value,
            "training_location": TrainingLocation.SMALL_FIELD.value,
            "difficulty": Difficulty.INTERMEDIATE.value,
            "target_skills": ["shooting", "dribbling"]
        },
        "description": "Club player with access to training facilities"
    },
    
    "advanced_player": {
        "name": "Advanced Player",
        "preferences": {
            "duration": 60,
            "available_equipment": [eq.value for eq in Equipment],  # All equipment
            "training_style": TrainingStyle.GAME_PREP.value,
            "training_location": TrainingLocation.FULL_FIELD.value,
            "difficulty": Difficulty.ADVANCED.value,
            "target_skills": ["passing", "shooting", "fitness"]
        },
        "description": "Competitive player with full facility access"
    },
    
    "limited_equipment_player": {
        "name": "Limited Equipment Player",
        "preferences": {
            "duration": 30,
            "available_equipment": [Equipment.BALL.value],  # Only ball
            "training_style": TrainingStyle.MEDIUM_INTENSITY.value,
            "training_location": TrainingLocation.SMALL_ROOM.value,
            "difficulty": Difficulty.INTERMEDIATE.value,
            "target_skills": ["ball_mastery", "first_touch"]
        },
        "description": "Player training indoors with minimal equipment"
    }
}

def create_session_preferences(profile: Dict[str, Any]) -> SessionPreferences:
    """Create SessionPreferences object from profile data"""
    return SessionPreferences(
        duration=profile["preferences"]["duration"],
        available_equipment=profile["preferences"]["available_equipment"],
        training_style=profile["preferences"]["training_style"],
        training_location=profile["preferences"]["training_location"],
        difficulty=profile["preferences"]["difficulty"],
        target_skills=profile["preferences"]["target_skills"]
    )

def print_session_details(profile_name: str, session: TrainingSession, profile: Dict[str, Any]):
    """Print detailed information about the generated session in a clear, structured format"""
    print(f"\n{'='*100}")
    print(f"{'SESSION DETAILS':^100}")
    print(f"{'='*100}")
    
    # Profile Section
    print(f"\n{'PLAYER PROFILE':^100}")
    print(f"{'-'*100}")
    print(f"Name: {profile['name']}")
    print(f"Description: {profile['description']}")
    
    # Preferences Section
    print(f"\n{'TRAINING PREFERENCES':^100}")
    print(f"{'-'*100}")
    print(f"⏱  Duration Goal: {profile['preferences']['duration']} minutes")
    print(f"📍  Location: {profile['preferences']['training_location']}")
    print(f"🎯  Difficulty Level: {profile['preferences']['difficulty']}")
    print(f"⚽  Available Equipment: {', '.join(profile['preferences']['available_equipment'])}")
    print(f"💪  Training Style: {profile['preferences']['training_style']}")
    print(f"🔄  Target Skills: {', '.join(profile['preferences']['target_skills'])}")
    
    # Generated Session Section
    print(f"\n{'GENERATED SESSION':^100}")
    print(f"{'-'*100}")
    print(f"⏱  Total Session Duration: {session.total_duration} minutes")
    print(f"📝  Number of Drills: {len(session.drills)}")
    
    # Drills Section
    print(f"\n{'TRAINING DRILLS':^100}")
    print(f"{'-'*100}")
    
    for i, drill in enumerate(session.drills, 1):
        print(f"\n🔸 Drill {i}: {drill.title}")
        print(f"   {'Duration':15} │ Original: {drill.original_duration:2d} min │ Adjusted: {drill.adjusted_duration:2d} min")
        print(f"   {'Difficulty':15} │ {drill.difficulty.title()}")
        print(f"   {'Equipment':15} │ {', '.join(drill.required_equipment)}")
        print(f"   {'Intensity':15} │ {drill.intensity_modifier:.2f}x modifier")
        
        # Calculate percentage of total session
        percentage = (drill.adjusted_duration / session.total_duration) * 100
        print(f"   {'Time Share':15} │ {percentage:.1f}% of session")
        
        if i < len(session.drills):  # Don't print after last drill
            print(f"   {'-' * 50}")
    
    # Session Summary
    print(f"\n{'SESSION SUMMARY':^100}")
    print(f"{'-'*100}")
    print(f"✓ Total Duration: {session.total_duration}/{profile['preferences']['duration']} minutes")
    print(f"✓ Average Intensity Modifier: {sum(d.intensity_modifier for d in session.drills)/len(session.drills):.2f}x")
    print(f"✓ Equipment Utilization: {len(set(eq for d in session.drills for eq in d.required_equipment))} types used")
    
    print(f"\n{'='*100}\n")

@pytest.mark.asyncio
async def test_session_generation_for_profiles():
    """Test session generation for different user profiles"""
    db = SessionLocal()
    try:
        generator = SessionGenerator(db)
        
        for profile_name, profile in USER_PROFILES.items():
            print(f"\nTesting profile: {profile_name}")
            
            # Create preferences from profile
            preferences = create_session_preferences(profile)
            
            # Generate session
            session = await generator.generate_session(preferences)
        
            # Print detailed session information
            print_session_details(profile_name, session, profile)
            
        # Assertions
            assert session is not None, f"Session should be generated for {profile_name}"
            assert len(session.drills) > 0, f"Session should contain drills for {profile_name}"
            assert session.total_duration <= preferences.duration, \
                f"Session duration ({session.total_duration}) should not exceed preferred duration ({preferences.duration})"
            
            # Verify drill suitability
            for drill in session.drills:
                # Equipment check
                assert all(eq in preferences.available_equipment for eq in drill.required_equipment), \
                    f"Drill {drill.title} requires unavailable equipment"
                
                # Location check
                assert preferences.training_location in drill.suitable_locations, \
                f"Drill {drill.title} not suitable for location {preferences.training_location}"
            
                # Verify intensity modification
                assert hasattr(drill, 'intensity_modifier'), \
                    f"Drill {drill.title} should have an intensity modifier"
                
                # Duration check
                assert drill.adjusted_duration >= 5, \
                    f"Drill {drill.title} duration too short: {drill.adjusted_duration} minutes"

    finally:
        db.close()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 