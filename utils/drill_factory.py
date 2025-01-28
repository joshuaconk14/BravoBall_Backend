from typing import List, Optional, Dict, Tuple
from enum import Enum
from models import (
    DrillType, TrainingLocation, TrainingStyle, Difficulty, Equipment,
    TrainingDuration, SkillCategory, PassingSubSkill, ShootingSubSkill,
    DribblingSubSkill, FirstTouchSubSkill, FitnessSubSkill
)

class DrillBuilder:
    def __init__(self, title: str):
        self.drill = {
            "title": title,
            "description": "",
            "drill_type": "TIME_BASED",
            "duration": 0,
            "default_sets": 3,
            "default_reps": 5,
            "default_duration": 120,
            "rest_between_sets": 60,  # Default 60 seconds rest
            "required_equipment": [],
            "suitable_locations": [],
            "intensity_level": "medium",
            "suitable_training_styles": [],
            "difficulty": "beginner",
            "skill_focus": [],  # List of {category: str, sub_skill: str, is_primary: bool}
            "instructions": [],
            "tips": [],
            "variations": []
        }

    def with_description(self, description: str):
        self.drill["description"] = description
        return self

    def with_type(self, drill_type: DrillType):
        self.drill["drill_type"] = drill_type
        return self

    def with_duration(self, duration: TrainingDuration):
        self.drill["duration"] = duration
        return self

    def with_sets(self, sets: int):
        self.drill["default_sets"] = sets
        return self

    def with_reps(self, reps: int):
        self.drill["default_reps"] = reps
        return self

    def with_equipment(self, *equipment: Equipment):
        self.drill["required_equipment"] = list(equipment)
        return self

    def with_suitable_locations(self, *locations: TrainingLocation):
        self.drill["suitable_locations"] = list(locations)
        return self

    def with_intensity(self, intensity: str):
        self.drill["intensity_level"] = intensity
        return self

    def with_training_styles(self, *styles: TrainingStyle):
        self.drill["suitable_training_styles"] = list(styles)
        return self

    def with_difficulty(self, difficulty: Difficulty):
        self.drill["difficulty"] = difficulty
        return self

    def with_primary_skill(self, category: SkillCategory, sub_skill: str):
        """Add the primary skill focus for the drill"""
        # Remove any existing primary skills first
        self.drill["skill_focus"] = [skill for skill in self.drill["skill_focus"] if not skill["is_primary"]]
        self.drill["skill_focus"].append({
            "category": category.value,
            "sub_skill": sub_skill,
            "is_primary": True
        })
        return self

    def with_secondary_skill(self, category: SkillCategory, sub_skill: str):
        """Add a secondary skill that is trained by this drill"""
        self.drill["skill_focus"].append({
            "category": category.value,
            "sub_skill": sub_skill,
            "is_primary": False
        })
        return self

    def with_secondary_skills(self, *skills: Tuple[SkillCategory, str]):
        """Add multiple secondary skills at once
        Usage: with_secondary_skills(
            (SkillCategory.FIRST_TOUCH, FirstTouchSubSkill.GROUND_CONTROL),
            (SkillCategory.FITNESS, FitnessSubSkill.AGILITY)
        )
        """
        for category, sub_skill in skills:
            self.with_secondary_skill(category, sub_skill)
        return self

    def clear_secondary_skills(self):
        """Remove all secondary skills from the drill"""
        self.drill["skill_focus"] = [skill for skill in self.drill["skill_focus"] if skill["is_primary"]]
        return self

    def with_instructions(self, *instructions: str):
        self.drill["instructions"] = list(instructions)
        return self

    def with_tips(self, *tips: str):
        self.drill["tips"] = list(tips)
        return self

    def with_variations(self, *variations: str):
        self.drill["variations"] = list(variations)
        return self

    def with_rest(self, seconds: int):
        self.drill["rest_between_sets"] = seconds
        return self

    def build(self):
        return self.drill 