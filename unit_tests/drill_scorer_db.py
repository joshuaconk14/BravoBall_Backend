import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from sqlalchemy.orm import Session
from models import (
    Drill, 
    SessionPreferences, 
    DrillSkillFocus, 
    TrainingLocation,
    TrainingStyle,
    Difficulty
)
from utils.drill_scorer import DrillScorer
from db import get_db

class TestDrillScorerWithDB:
    """Test suite for DrillScorer with actual database interactions"""

    @pytest.fixture
    def db_session(self):
        """Get a database session"""
        db = next(get_db())
        try:
            yield db
        finally:
            db.close()

    @pytest.fixture
    def base_preferences(self):
        """Base session preferences fixture"""
        return SessionPreferences(
            duration=60,
            available_equipment=["BALL", "CONES"],
            training_style=TrainingStyle.MEDIUM_INTENSITY,
            training_location=TrainingLocation.SMALL_FIELD.value,  # Using enum value
            difficulty=Difficulty.INTERMEDIATE.value,
            target_skills=[{
                "category": "passing",
                "sub_skills": ["short_passing", "wall_passing"]
            }]
        )

    def test_rank_drills_from_db(self, db_session: Session, base_preferences):
        """Test ranking drills fetched from the database"""
        # Query all drills from the database
        drills = db_session.query(Drill).all()
        
        # Ensure we have drills to test with
        assert len(drills) > 0, "No drills found in database"
        
        # Create scorer and rank drills
        scorer = DrillScorer(base_preferences)
        ranked_drills = scorer.rank_drills(drills)
        
        # Print detailed rankings for inspection
        print("\nDatabase Drill Rankings:")
        for rank, entry in enumerate(ranked_drills, 1):
            print(f"\n{rank}. {entry['drill'].title}")
            print(f"Total Score: {entry['total_score']}")
            print("Score Breakdown:")
            for category, score in entry['scores'].items():
                if category != 'total':
                    print(f"  {category}: {score}")
            
            # Print drill details for context
            print("\nDrill Details:")
            print(f"  Primary Skill: {[sf.category + '/' + sf.sub_skill for sf in entry['drill'].skill_focus if sf.is_primary]}")
            print(f"  Secondary Skills: {[sf.category + '/' + sf.sub_skill for sf in entry['drill'].skill_focus if not sf.is_primary]}")
            print(f"  Equipment: {entry['drill'].required_equipment}")
            print(f"  Locations: {[loc for loc in entry['drill'].suitable_locations]}")  # Print raw location values
            print(f"  Difficulty: {entry['drill'].difficulty}")
            print(f"  Duration: {entry['drill'].duration} minutes")

        # Basic assertions to verify ranking logic
        assert all(ranked_drills[i]['total_score'] >= ranked_drills[i+1]['total_score'] 
                  for i in range(len(ranked_drills)-1)), "Drills should be sorted by descending score"

    def test_filter_and_rank_drills(self, db_session: Session, base_preferences):
        """Test filtering drills by criteria before ranking"""
        # Get all drills first
        all_drills = db_session.query(Drill).all()
        
        # Filter drills in Python
        matching_drills = []
        for drill in all_drills:
            # Check difficulty match
            if drill.difficulty != base_preferences.difficulty:
                continue
                
            # Check location match - compare with enum value
            if not drill.suitable_locations or base_preferences.training_location not in drill.suitable_locations:
                continue
                
            matching_drills.append(drill)
        
        assert len(matching_drills) > 0, "No matching drills found in database"
        
        # Rank the filtered drills
        scorer = DrillScorer(base_preferences)
        ranked_drills = scorer.rank_drills(matching_drills)
        
        print("\nFiltered Drill Rankings (Matching Difficulty and Location):")
        for rank, entry in enumerate(ranked_drills, 1):
            print(f"\n{rank}. {entry['drill'].title}")
            print(f"Total Score: {entry['total_score']}")
            print("Drill Details:")
            print(f"  Difficulty: {entry['drill'].difficulty}")
            print(f"  Locations: {[TrainingLocation(loc).name for loc in entry['drill'].suitable_locations]}")  # Convert to enum names
            print(f"  Equipment: {entry['drill'].required_equipment}")
            print(f"  Duration: {entry['drill'].duration} minutes")
            
        # Verify all ranked drills match our basic criteria
        for entry in ranked_drills:
            drill = entry['drill']
            assert drill.difficulty == base_preferences.difficulty, f"Drill '{drill.title}' has wrong difficulty: {drill.difficulty}"
            assert base_preferences.training_location in drill.suitable_locations, f"Drill '{drill.title}' doesn't support location: {base_preferences.training_location}"

    def test_skill_based_ranking(self, db_session: Session, base_preferences):
        """Test ranking drills based on skill focus"""
        # Query drills that have skill focus matching user preferences
        target_category = base_preferences.target_skills[0]["category"]
        matching_drills = (
            db_session.query(Drill)
            .join(DrillSkillFocus)
            .filter(DrillSkillFocus.category == target_category)
            .all()
        )
        
        assert len(matching_drills) > 0, f"No drills found focusing on {target_category}"
        
        # Rank the skill-matched drills
        scorer = DrillScorer(base_preferences)
        ranked_drills = scorer.rank_drills(matching_drills)
        
        print(f"\nSkill-Based Rankings (Category: {target_category}):")
        for rank, entry in enumerate(ranked_drills, 1):
            print(f"\n{rank}. {entry['drill'].title}")
            print(f"Primary Skill Score: {entry['scores']['primary_skill']}")
            print(f"Secondary Skill Score: {entry['scores']['secondary_skill']}")
            
        # Verify skill scoring
        for entry in ranked_drills:
            has_matching_skill = False
            for skill_focus in entry['drill'].skill_focus:
                if skill_focus.category == target_category:
                    has_matching_skill = True
                    break
            assert has_matching_skill, f"All drills should have a skill focus in {target_category}"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 