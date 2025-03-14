from typing import List, Dict, Any
from models import Drill, SessionPreferences, DrillSkillFocus

class DrillScorer:
    """
    Scores drills based on how well they match user preferences and requirements.
    Higher scores indicate better matches.
    """

    def __init__(self, preferences: SessionPreferences):
        self.preferences = preferences
        # Weights for different scoring factors (can be adjusted)
        self.weights = {
            "primary_skill": 5.0,      # Primary skill match is most important
            "secondary_skill": 2.0,    # Secondary skills provide additional value
            "equipment": 4.0,          # Equipment availability is crucial
            "location": 4.0,           # Location match is crucial
            "difficulty": 3.0,         # Difficulty appropriateness
            "intensity": 2.0,          # Intensity match
            "duration": 1.0,           # Duration fit
            "training_style": 2.0      # Training style match
        }
        self.ADAPTABLE_EQUIPMENT = {"CONES", "WALL"}
        self.CRITICAL_EQUIPMENT = {"GOALS", "BALL"}

    def score_drill(self, drill: Drill) -> Dict[str, float]:
        """
        Calculate a detailed score for a drill based on how well it matches preferences.
        Returns a dictionary with individual scores and total.
        """
        scores = {
            key: self._calculate_score(key, drill) * weight
            for key, weight in self.weights.items()
        }
        
        # Special handling for equipment score
        equipment_score = scores["equipment"] / self.weights["equipment"]
        if 0 < equipment_score < 1:
            scores["equipment"] *= 0.8
        
        scores["total"] = sum(scores.values())
        return scores

    def _calculate_score(self, score_type: str, drill: Drill) -> float:
        """Calculate individual score components"""
        score_methods = {
            "primary_skill": lambda: self._score_skills(drill.skill_focus)["primary"],
            "secondary_skill": lambda: self._score_skills(drill.skill_focus)["secondary"],
            "equipment": lambda: self._score_equipment(drill.required_equipment),
            "location": lambda: self._score_location(drill.suitable_locations),
            "difficulty": lambda: self._score_difficulty(drill.difficulty),
            "intensity": lambda: self._score_intensity(drill.intensity_level),
            "duration": lambda: self._score_duration(drill.duration),
            "training_style": lambda: self._score_training_style(drill.suitable_training_styles)
        }
        return score_methods[score_type]()

    def _score_skills(self, skill_focus: List[DrillSkillFocus]) -> Dict[str, float]:
        """Score based on skill matches"""
        if not skill_focus:  # Handles both None and empty list
            return {"primary": 0.0, "secondary": 0.0}

        # Rest of the method remains the same
        primary_skill = next((focus for focus in skill_focus if focus.is_primary), None)
        if not primary_skill:
            return {"primary": 0.0, "secondary": 0.0}

        # Score primary skill
        primary_score = float(any(primary_skill.category == target for target in self.preferences.target_skills))

        # Score secondary skills
        secondary_skills = [focus for focus in skill_focus if not focus.is_primary]
        secondary_score = 0.0
        if secondary_skills:
            matches = sum(1 for skill in secondary_skills 
                        for target in self.preferences.target_skills 
                        if skill.category == target)
            secondary_score = min(matches * 0.5, 0.5)  # Cap at 0.5

        return {"primary": primary_score, "secondary": secondary_score}

    def _score_equipment(self, required_equipment: List[str]) -> float:
        """
        Score based on equipment availability with flexibility for limited equipment scenarios.
        Returns:
        - 1.0: All equipment available
        - 0.8: Only basic equipment needed (just ball)
        - 0.6: Missing some equipment but drill can be adapted (e.g., cones can be replaced)
        - 0.0: Missing critical equipment that cannot be substituted (e.g., goals)
        """
        if not required_equipment:  # No equipment needed
            return 1.0
            
        # Check if only ball is required
        if set(required_equipment) == {"BALL"}:
            return 0.8 if "BALL" in self.preferences.available_equipment else 0.0
            
        # Check available equipment
        missing_equipment = set(required_equipment) - set(self.preferences.available_equipment)
        if not missing_equipment:  # Has all equipment
            return 1.0
            
        # Check if missing equipment is adaptable
        if missing_equipment & self.CRITICAL_EQUIPMENT:  # Missing critical equipment
            return 0.0
            
        # If only missing adaptable equipment, give partial score
        if missing_equipment <= self.ADAPTABLE_EQUIPMENT:
            return 0.6
            
        return 0.0

    def _score_location(self, suitable_locations: List[str]) -> float:
        """Score based on location match"""
        if not suitable_locations:  # Handles both None and empty list
            return 0.0
        return float(self.preferences.training_location in suitable_locations)

    def _score_difficulty(self, difficulty: str) -> float:
        """Score based on difficulty match"""
        if not difficulty:  # Handle None value
            return 0.0
        difficulties = ["beginner", "intermediate", "advanced"]
        try:
            drill_idx = difficulties.index(difficulty)
            pref_idx = difficulties.index(self.preferences.difficulty)
            return 1.0 if drill_idx == pref_idx else 0.5
        except ValueError:
            raise KeyError(f"Invalid difficulty value: {difficulty}")

    def _score_intensity(self, intensity: str) -> float:
        """Score based on intensity match"""
        if not intensity:  # Handle None value
            return 0.0
        intensities = {
            "low": ["LOW_INTENSITY"],
            "medium": ["MEDIUM_INTENSITY"],
            "high": ["HIGH_INTENSITY", "GAME_PREP"]
        }
        return float(self.preferences.training_style in intensities.get(intensity, []))

    def _score_duration(self, duration: int) -> float:
        """Score how well the drill duration fits within session time"""
        if duration > self.preferences.duration:
            return 0.0
            
        portion = duration / self.preferences.duration
        if portion < 0.1:  # Too short
            return 0.5
        elif portion > 0.5:  # Too long
            return 0.7
        else:  # Just right
            return 1.0

    def _score_training_style(self, training_styles: List[str]) -> float:
        """Score based on training style match"""
        if not training_styles:  # Handles both None and empty list
            return 0.0
        return float(self.preferences.training_style in training_styles)

    def rank_drills(self, drills: List[Drill]) -> List[Dict[str, Any]]:
        """
        Rank a list of drills based on their scores.
        Returns list of dicts with drill and score information, sorted by total score.
        """
        return sorted([
            {
                "drill": drill,
                "scores": (scores := self.score_drill(drill)),
                "total_score": scores["total"]
            }
            for drill in drills
        ], key=lambda x: x["total_score"], reverse=True) 
    