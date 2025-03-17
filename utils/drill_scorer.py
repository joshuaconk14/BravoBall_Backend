from typing import List, Dict, Any
from models import Drill, SessionPreferences, DrillSkillFocus
from db import SessionLocal

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
            "equipment": lambda: self._score_equipment(drill.equipment),
            "location": lambda: self._score_location(drill.suitable_locations),
            "difficulty": lambda: self._score_difficulty(drill.difficulty),
            "intensity": lambda: self._score_intensity(drill.intensity),
            "duration": lambda: self._score_duration(drill.duration),
            "training_style": lambda: self._score_training_style(drill.training_styles)
        }
        return score_methods[score_type]()

    def _score_skills(self, skill_focus: List[DrillSkillFocus]) -> Dict[str, float]:
        """Score based on skill matches"""
        if not skill_focus:  # Handles both None and empty list
            return {"primary": 0.5, "secondary": 0.0}  # Default primary score for drills with no skill focus

        try:
            # Find primary skill
            primary_skill = next((focus for focus in skill_focus if focus.is_primary), None)
            if not primary_skill:
                return {"primary": 0.5, "secondary": 0.0}  # Default primary score if no primary skill found
            
            # Handle case where target_skills might be None
            if not self.preferences.target_skills:
                return {"primary": 0.5, "secondary": 0.0}  # Default scores if no target skills
            
            # Score primary skill - normalize to lowercase for comparison
            primary_category = primary_skill.category.lower() if primary_skill.category else ""
            target_skills_lower = [target.lower() if target else "" for target in self.preferences.target_skills]
            
            # Check if any target skills exist in the database
            # If not, give a partial score to all drills to ensure some are returned
            db = SessionLocal()
            try:
                matching_drills_count = db.query(Drill).join(Drill.skill_focus).filter(
                    Drill.skill_focus.any(category=self.preferences.target_skills[0])
                ).count()
                
                # If we have very few or no matching drills, be more lenient
                if matching_drills_count < 3:
                    primary_score = 0.5  # Give a partial score to ensure some drills are returned
                else:
                    primary_score = float(any(primary_category == target for target in target_skills_lower))
            finally:
                db.close()
            
            # Score secondary skills
            secondary_skills = [focus for focus in skill_focus if not focus.is_primary]
            secondary_score = 0.0
            if secondary_skills:
                matches = sum(1 for skill in secondary_skills 
                            for target in target_skills_lower 
                            if skill.category and skill.category.lower() == target)
                secondary_score = min(matches * 0.5, 0.5)  # Cap at 0.5

            return {"primary": primary_score, "secondary": secondary_score}
        except (AttributeError, TypeError, IndexError) as e:
            # Handle any unexpected errors in skill matching
            print(f"Error in skill scoring: {str(e)}")
            return {"primary": 0.5, "secondary": 0.0}

    def _score_equipment(self, required_equipment: List[str]) -> float:
        """
        Score based on equipment availability with flexibility for limited equipment scenarios.
        Returns:
        - 1.0: All equipment available
        - 0.8: Only basic equipment needed (just ball)
        - 0.6: Missing some equipment but drill can be adapted (e.g., cones can be replaced)
        - 0.0: Missing critical equipment that cannot be substituted (e.g., goals)
        """
        if not required_equipment:  # No equipment needed or None
            return 1.0
            
        # Check if only ball is required
        if set(required_equipment) == {"BALL"} or set(required_equipment) == {"ball"}:
            return 0.8 if "ball" in self.preferences.available_equipment or "BALL" in self.preferences.available_equipment else 0.0
            
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
            return 0.5  # Default score for drills with no location specified
        return float(self.preferences.training_location in suitable_locations)

    def _score_difficulty(self, difficulty: str) -> float:
        """Score based on difficulty match"""
        if not difficulty:  # Handle None value
            return 0.5  # Default score for drills with no difficulty
            
        difficulties = ["beginner", "intermediate", "advanced"]
        try:
            # Normalize difficulty to lowercase
            normalized_difficulty = difficulty.lower()
            normalized_preference = self.preferences.difficulty.lower() if self.preferences.difficulty else "beginner"
            
            if normalized_difficulty not in difficulties:
                return 0.5  # Unknown difficulty, give average score
                
            drill_idx = difficulties.index(normalized_difficulty)
            pref_idx = difficulties.index(normalized_preference)
            
            # Exact match gets full score
            if drill_idx == pref_idx:
                return 1.0
                
            # One level difference gets partial score
            if abs(drill_idx - pref_idx) == 1:
                return 0.5
                
            # Two level difference gets low score
            return 0.2
        except (ValueError, AttributeError):
            return 0.5  # Default score for invalid difficulty values

    def _score_intensity(self, intensity: str) -> float:
        """Score based on intensity match"""
        if not intensity:  # Handle None value
            return 0.5  # Default score for drills with no intensity
        intensities = {
            "low": ["LOW_INTENSITY", "low_intensity"],
            "medium": ["MEDIUM_INTENSITY", "medium_intensity"],
            "high": ["HIGH_INTENSITY", "high_intensity", "GAME_PREP", "game_prep"]
        }
        for level, styles in intensities.items():
            if intensity.lower() in [s.lower() for s in styles]:
                return float(self.preferences.training_style.lower() in [s.lower() for s in styles])
        return 0.0

    def _score_duration(self, duration: int) -> float:
        """Score how well the drill duration fits within session time"""
        if duration is None:
            return 0.5  # Default score for drills with no duration
            
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
            return 0.5  # Default score for drills with no training style
        
        # Normalize training styles to lowercase for comparison
        normalized_styles = [style.lower() if style else "" for style in training_styles]
        normalized_preference = self.preferences.training_style.lower() if self.preferences.training_style else ""
        
        return float(normalized_preference in normalized_styles)

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
    