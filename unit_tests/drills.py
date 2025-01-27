"""
Unit tests for drills. Run with `pytest unit_tests/drills.py -s`
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import text
from db import SessionLocal
from models import Drill, DrillCategory

def test_can_query_drills():
    """Test that we can successfully query drills from the database"""
    db = SessionLocal()
    try:
        # Get all drills
        drills = db.query(Drill).all()
        
        # Print drill information for debugging
        print("\nFound drills:")
        for drill in drills:
            print(f"\n{'='*50}")
            print(f"Drill: {drill.title}")
            print(f"Description: {drill.description}")
            print(f"Category: {drill.category.name if drill.category else 'No category'}")
            print(f"Duration: {drill.duration} minutes")
            print(f"Type: {drill.drill_type}")
            print(f"Intensity: {drill.intensity_level}")
            print(f"Equipment: {drill.required_equipment}")
            print(f"Locations: {drill.suitable_locations}")
            print(f"Difficulty: {drill.difficulty}")
            print(f"Skill Focus: {drill.skill_focus}")
            print(f"Instructions: {drill.instructions}")
            print(f"Tips: {drill.tips}")
            if drill.variations:
                print(f"Variations: {drill.variations}")
            print(f"{'='*50}\n")

        # Basic assertions
        assert isinstance(drills, list), "Query should return a list"
        assert len(drills) == 3, "Should have exactly 3 drills"
        print(f"\nTotal drills found: {len(drills)}")

        # Test specific drills exist
        drill_titles = {drill.title for drill in drills}
        expected_titles = {
            "Wall Pass Mastery",
            "Power Shot Development",
            "Cone ZigZag Sprint"
        }
        assert drill_titles == expected_titles, f"Missing some expected drills. Found: {drill_titles}"

        # Get all categories
        categories = db.query(DrillCategory).all()
        print(f"\nTotal categories found: {len(categories)}")
        print("\nCategories:")
        for category in categories:
            print(f"- {category.name}")
            # Print drills in this category
            category_drills = db.query(Drill).filter(Drill.category_id == category.id).all()
            for drill in category_drills:
                print(f"  * {drill.title}")

        # Test filtering
        # By difficulty
        beginner_drills = db.query(Drill).filter(Drill.difficulty == "beginner").all()
        print(f"\nBeginner drills: {[d.title for d in beginner_drills]}")
        
        # Get drills that require balls
        drills = db.query(Drill)
        ball_drills = []
        for drill in drills:
            if "BALL" in drill.required_equipment:
                ball_drills.append(drill)
        print(f"\nDrills requiring a ball: {[d.title for d in ball_drills]}")

    finally:
        db.close()

if __name__ == "__main__":
    test_can_query_drills() 