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
            "type": "time_based",
            "duration": 0,
            "sets": None,
            "reps": None,
            "rest": None,
            "equipment": [],
            "suitable_locations": [],
            "intensity": "medium",
            "training_styles": [],
            "difficulty": "beginner",
            "skill_focus": [],  # List of {category: str, sub_skill: str, is_primary: bool}
            "instructions": [],
            "tips": [],
            "common_mistakes": [],
            "progression_steps": [],
            "variations": [],
            "video_url": None,
            "thumbnail_url": None
        }

    def with_description(self, description: str):
        self.drill["description"] = description
        return self

    def with_type(self, drill_type: DrillType):
        self.drill["type"] = drill_type.lower()
        return self

    def with_duration(self, duration: int):
        self.drill["duration"] = duration
        return self

    def with_sets(self, sets: int):
        self.drill["sets"] = sets
        return self

    def with_reps(self, reps: int):
        self.drill["reps"] = reps
        return self

    def with_equipment(self, *equipment: Equipment):
        self.drill["equipment"] = [eq.lower() for eq in equipment]
        return self

    def with_suitable_locations(self, *locations: TrainingLocation):
        self.drill["suitable_locations"] = [loc.lower() for loc in locations]
        return self

    def with_intensity(self, intensity: str):
        self.drill["intensity"] = intensity.lower()
        return self

    def with_training_styles(self, *styles: TrainingStyle):
        self.drill["training_styles"] = [style.lower() for style in styles]
        return self

    def with_difficulty(self, difficulty: Difficulty):
        self.drill["difficulty"] = difficulty.lower()
        return self

    def with_primary_skill(self, category: SkillCategory, sub_skill: str):
        """Add the primary skill focus for the drill"""
        # Remove any existing primary skills first
        self.drill["skill_focus"] = [skill for skill in self.drill["skill_focus"] if not skill["is_primary"]]
        self.drill["skill_focus"].append({
            "category": category.value.lower(),
            "sub_skill": sub_skill.lower(),
            "is_primary": True
        })
        return self

    def with_secondary_skill(self, category: SkillCategory, sub_skill: str):
        """Add a secondary skill that is trained by this drill"""
        self.drill["skill_focus"].append({
            "category": category.value.lower(),
            "sub_skill": sub_skill.lower(),
            "is_primary": False
        })
        return self

    def with_secondary_skills(self, *skills: Tuple[SkillCategory, str]):
        """Add multiple secondary skills at once"""
        for category, sub_skill in skills:
            self.with_secondary_skill(category, sub_skill)
        return self

    def with_instructions(self, *instructions: str):
        self.drill["instructions"] = list(instructions)
        return self

    def with_tips(self, *tips: str):
        self.drill["tips"] = list(tips)
        return self

    def with_common_mistakes(self, *mistakes: str):
        self.drill["common_mistakes"] = list(mistakes)
        return self

    def with_progression_steps(self, *steps: str):
        self.drill["progression_steps"] = list(steps)
        return self

    def with_variations(self, *variations: str):
        self.drill["variations"] = list(variations)
        return self

    def with_rest(self, seconds: int):
        self.drill["rest"] = seconds
        return self

    def with_video_url(self, url: str):
        self.drill["video_url"] = url
        return self

    def with_thumbnail_url(self, url: str):
        self.drill["thumbnail_url"] = url
        return self

    def build(self):
        return self.drill 