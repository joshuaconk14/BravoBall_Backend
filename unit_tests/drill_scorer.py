import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from models import SessionPreferences, Drill, DrillSkillFocus, SkillCategory, TrainingStyle
from utils.drill_scorer import DrillScorer
from sample_drills import sample_drills

def create_test_preferences(
    target_skills=None,
    available_equipment=None,
    training_location="INDOOR_COURT",
    difficulty="intermediate",
    training_style="MEDIUM_INTENSITY",
    duration=60
):
    """Helper function to create test preferences"""
    if target_skills is None:
        target_skills = [
            {
                "category": "passing",
                "sub_skills": ["short_passing", "wall_passing"]
            }
        ]
    if available_equipment is None:
        available_equipment = ["BALL", "CONES", "WALL"]

    return SessionPreferences(
        duration=duration,
        available_equipment=available_equipment,
        training_style=training_style,
        training_location=training_location,
        difficulty=difficulty,
        target_skills=target_skills
    )

def create_test_drill(
    title: str,
    primary_skill: tuple = None,  # (category, sub_skill)
    secondary_skills: list = None,  # list of (category, sub_skill)
    difficulty: str = "intermediate",
    duration: int = 15,
    equipment: list = None,
    locations: list = None,
    intensity: str = "medium",
    training_styles: list = None
) -> Drill:
    """Helper function to create a complete test drill"""
    if equipment is None:
        equipment = ["BALL"]
    if locations is None:
        locations = ["INDOOR_COURT", "SMALL_FIELD"]
    if training_styles is None:
        training_styles = ["MEDIUM_INTENSITY"]

    drill = Drill(
        title=title,
        description=f"Test drill: {title}",
        duration=duration,
        intensity_level=intensity,
        suitable_training_styles=training_styles,
        drill_type="TIME_BASED",
        default_sets=3,
        default_reps=0,
        required_equipment=equipment,
        suitable_locations=locations,
        difficulty=difficulty,
        instructions=["Test instruction 1", "Test instruction 2"],
        tips=["Test tip 1", "Test tip 2"]
    )

    # Add skill focus
    skill_focus = []
    if primary_skill:
        skill_focus.append(
            DrillSkillFocus(
                drill_id=1,
                category=primary_skill[0],
                sub_skill=primary_skill[1],
                is_primary=True
            )
        )
    
    if secondary_skills:
        for category, sub_skill in secondary_skills:
            skill_focus.append(
                DrillSkillFocus(
                    drill_id=1,
                    category=category,
                    sub_skill=sub_skill,
                    is_primary=False
                )
            )
    
    drill.skill_focus = skill_focus
    return drill

def test_perfect_match():
    """Test scoring for a drill that perfectly matches preferences"""
    # Create preferences that match the test drill
    preferences = create_test_preferences(
        target_skills=[{
            "category": "passing",
            "sub_skills": ["wall_passing", "short_passing"]
        }],
        available_equipment=["BALL", "WALL"],
        training_location="INDOOR_COURT",
        difficulty="intermediate",
        training_style="MEDIUM_INTENSITY",
        duration=30
    )
    
    scorer = DrillScorer(preferences)
    
    drill = create_test_drill(
        title="Perfect Match Drill",
        primary_skill=("passing", "wall_passing"),
        secondary_skills=[("passing", "short_passing")],
        equipment=["BALL", "WALL"],
        locations=["INDOOR_COURT"],
        difficulty="intermediate",
        duration=15,
        training_styles=["MEDIUM_INTENSITY"]
    )
    
    scores = scorer.score_drill(drill)
    
    # Should get maximum scores for all categories
    assert scores["primary_skill"] == 5.0  # Perfect primary skill match
    assert scores["location"] == 4.0       # Perfect location match
    assert scores["equipment"] == 4.0      # Has all equipment
    assert scores["difficulty"] == 3.0     # Perfect difficulty match
    assert scores["training_style"] == 2.0 # Perfect style match
    assert scores["duration"] == 1.0       # Good duration fit
    
    # Print detailed scores for debugging
    print("\nPerfect Match Test Scores:")
    for category, score in scores.items():
        print(f"{category}: {score}")

def test_equipment_mismatch():
    """Test scoring when user lacks required equipment"""
    preferences = create_test_preferences(
        available_equipment=["BALL"]  # Missing WALL
    )
    
    scorer = DrillScorer(preferences)
    drill = create_test_drill(
        title="Wall Pass Test",
        equipment=["BALL", "WALL"],
        primary_skill=("passing", "wall_passing")
    )
    
    scores = scorer.score_drill(drill)
    assert scores["equipment"] == 0.0  # Should get zero for missing equipment

def test_skill_scoring():
    """Test various skill matching scenarios"""
    preferences = create_test_preferences(
        target_skills=[
            {
                "category": "passing",
                "sub_skills": ["short_passing", "wall_passing"]
            },
            {
                "category": "first_touch",
                "sub_skills": ["ground_control", "one_touch_control"]
            }
        ]
    )
    
    scorer = DrillScorer(preferences)
    
    # Test primary skill match
    drill = create_test_drill(
        title="Test Primary Skill",
        primary_skill=("passing", "wall_passing")
    )
    scores = scorer.score_drill(drill)
    assert scores["primary_skill"] == 5.0  # Perfect primary match
    
    # Test secondary skill match
    drill = create_test_drill(
        title="Test Secondary Skills",
        primary_skill=("passing", "wall_passing"),
        secondary_skills=[
            ("first_touch", "ground_control"),
            ("first_touch", "one_touch_control")
        ]
    )
    scores = scorer.score_drill(drill)
    assert scores["secondary_skill"] == 2.0  # Two matching secondary skills

def test_difficulty_progression():
    """Test how scores change with different difficulty levels"""
    preferences = create_test_preferences(difficulty="intermediate")
    scorer = DrillScorer(preferences)
    
    # Test each difficulty level
    difficulties = ["beginner", "intermediate", "advanced"]
    scores = []
    
    for diff in difficulties:
        drill = create_test_drill(
            title=f"Test {diff}",
            difficulty=diff,
            primary_skill=("passing", "short_passing")
        )
        score = scorer.score_drill(drill)
        scores.append(score["difficulty"])
    
    # Print difficulty progression
    print("\nDifficulty Progression Scores:")
    for diff, score in zip(difficulties, scores):
        print(f"{diff}: {score}")
    
    # Perfect match should score highest
    assert scores[1] > scores[0]  # intermediate > beginner
    assert scores[1] > scores[2]  # intermediate > advanced

def test_duration_scoring():
    """Test how duration affects scoring"""
    preferences = create_test_preferences(duration=60)  # 60-minute session
    scorer = DrillScorer(preferences)
    
    # Test various durations
    durations = [5, 15, 30, 45]  # in minutes
    scores = []
    
    for dur in durations:
        drill = create_test_drill(
            title=f"{dur}min drill",
            duration=dur,
            primary_skill=("passing", "short_passing")
        )
        score = scorer.score_drill(drill)
        scores.append(score["duration"])
    
    # Print duration scores
    print("\nDuration Scores:")
    for dur, score in zip(durations, scores):
        print(f"{dur} minutes: {score}")
    
    # Ideal duration (15-30 mins for 60 min session) should score highest
    assert scores[1] >= scores[0]  # 15 mins > 5 mins
    assert scores[2] >= scores[3]  # 30 mins > 45 mins

def test_rank_drills():
    """Test the drill ranking functionality"""
    preferences = create_test_preferences(
        target_skills=[
            {
                "category": "passing",
                "sub_skills": ["short_passing", "wall_passing"]
            }
        ],
        available_equipment=["BALL", "WALL", "CONES"],
        training_location="INDOOR_COURT",
        difficulty="beginner"
    )
    
    scorer = DrillScorer(preferences)
    
    # Create a set of test drills with varying matches
    drills = [
        create_test_drill(
            title="Perfect Match",
            primary_skill=("passing", "wall_passing"),
            difficulty="beginner",
            equipment=["BALL", "WALL"]
        ),
        create_test_drill(
            title="Wrong Skill",
            primary_skill=("shooting", "power"),
            difficulty="beginner"
        ),
        create_test_drill(
            title="Wrong Difficulty",
            primary_skill=("passing", "wall_passing"),
            difficulty="advanced"
        ),
        create_test_drill(
            title="Missing Equipment",
            primary_skill=("passing", "wall_passing"),
            equipment=["BALL", "WALL", "GOALS"],
            difficulty="beginner"
        )
    ]
    
    # Score the drills
    ranked_drills = scorer.rank_drills(drills)
    
    # Print rankings
    print("\nDrill Rankings:")
    for rank, entry in enumerate(ranked_drills, 1):
        print(f"\n{rank}. {entry['drill'].title}")
        print(f"Total Score: {entry['total_score']}")
        print("Score Breakdown:")
        for category, score in entry['scores'].items():
            if category != 'total':
                print(f"  {category}: {score}")
    
    # First drill should have highest total score
    assert ranked_drills[0]['total_score'] >= ranked_drills[1]['total_score']
    assert ranked_drills[0]['drill'].title == "Perfect Match"  # Should be our perfect match drill

if __name__ == "__main__":
    pytest.main([__file__]) 