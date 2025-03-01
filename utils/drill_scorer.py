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

    def score_drill(self, drill: Drill) -> Dict[str, float]:
        """
        Calculate a detailed score for a drill based on how well it matches preferences.
        Returns a dictionary with individual scores and total.
        """
        scores = {}
        
        # Score primary and secondary skills
        skill_scores = self._score_skills(drill.skill_focus)
        scores["primary_skill"] = skill_scores["primary"] * self.weights["primary_skill"]
        scores["secondary_skill"] = skill_scores["secondary"] * self.weights["secondary_skill"]
        
        # Score equipment match
        scores["equipment"] = self._score_equipment(drill.required_equipment) * self.weights["equipment"]
        
        # Score location suitability
        scores["location"] = self._score_location(drill.suitable_locations) * self.weights["location"]
        
        # Score difficulty match
        scores["difficulty"] = self._score_difficulty(drill.difficulty) * self.weights["difficulty"]
        
        # Score intensity match
        scores["intensity"] = self._score_intensity(drill.intensity_level) * self.weights["intensity"]
        
        # Score duration fit
        scores["duration"] = self._score_duration(drill.duration) * self.weights["duration"]
        
        # Score training style match
        scores["training_style"] = self._score_training_style(drill.suitable_training_styles) * self.weights["training_style"]
        
        # Calculate total score
        scores["total"] = sum(scores.values())
        
        return scores

    def _score_skills(self, skill_focus: List[DrillSkillFocus]) -> Dict[str, float]:
        """Score based on skill matches"""
        if not skill_focus:  # Handles both None and empty list
            return {"primary": 0.0, "secondary": 0.0}

        # Rest of the method remains the same
        primary_skill = next((focus for focus in skill_focus if focus.is_primary), None)
        if not primary_skill:
            return {"primary": 0.0, "secondary": 0.0}

        # Score primary skill
        primary_score = 0.0
        for target in self.preferences.target_skills:
            # Simple string match with category
            if primary_skill.category == target:
                primary_score = 1.0
                break

        # Score secondary skills
        secondary_score = 0.0
        secondary_skills = [focus for focus in skill_focus if not focus.is_primary]
        if secondary_skills:
            matches = 0
            for skill in secondary_skills:
                for target in self.preferences.target_skills:
                    # Simple string match with category
                    if skill.category == target:
                        matches += 1
                        break
        
            secondary_score = min(matches * 0.5, 0.5)  # Cap at 0.5

        return {"primary": primary_score, "secondary": secondary_score}

    def _score_equipment(self, required_equipment: List[str]) -> float:
        """Score based on equipment availability"""
        if not required_equipment:  # Handles both None and empty list
            return 1.0
        return 1.0 if all(equip in self.preferences.available_equipment for equip in required_equipment) else 0.0

    def _score_location(self, suitable_locations: List[str]) -> float:
        """Score based on location match"""
        if not suitable_locations:  # Handles both None and empty list
            return 0.0
        return 1.0 if self.preferences.training_location in suitable_locations else 0.0

    def _score_difficulty(self, difficulty: str) -> float:
        """Score based on difficulty match"""
        if not difficulty:  # Handle None value
            return 0.0
        difficulties = ["beginner", "intermediate", "advanced"]
        try:
            drill_idx = difficulties.index(difficulty)
            pref_idx = difficulties.index(self.preferences.difficulty)
            diff = abs(drill_idx - pref_idx)
            return 1.0 if diff == 0 else 0.5
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
        return 1.0 if self.preferences.training_style in intensities.get(intensity, []) else 0.0

    def _score_duration(self, duration: int) -> float:
        """Score how well the drill duration fits within session time"""
        if duration <= self.preferences.duration:
            # Prefer drills that use a reasonable portion of available time
            portion = duration / self.preferences.duration
            if portion < 0.1:  # Too short
                return 0.5
            elif portion > 0.5:  # Too long
                return 0.7
            else:  # Just right
                return 1.0
        return 0.0  # Drill is too long

    def _score_training_style(self, training_styles: List[str]) -> float:
        """Score based on training style match"""
        if not training_styles:  # Handles both None and empty list
            return 0.0
        return 1.0 if self.preferences.training_style in training_styles else 0.0

    def rank_drills(self, drills: List[Drill]) -> List[Dict[str, Any]]:
        """
        Rank a list of drills based on their scores.
        Returns list of dicts with drill and score information, sorted by total score.
        """
        scored_drills = []
        for drill in drills:
            scores = self.score_drill(drill)
            scored_drills.append({
                "drill": drill,
                "scores": scores,
                "total_score": scores["total"]
            })
        
        # Sort by total score, highest first
        return sorted(scored_drills, key=lambda x: x["total_score"], reverse=True) 
    