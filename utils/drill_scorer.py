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
        """Score how well the drill's skills match user's target skills"""
        primary_score = 0.0
        secondary_score = 0.0
        
        for focus in skill_focus:
            # Check if this skill category is in user's target skills
            for target in self.preferences.target_skills:
                if focus.category == target["category"]:
                    # Check if specific sub-skill is targeted
                    if focus.sub_skill in target["sub_skills"]:
                        if focus.is_primary:
                            primary_score = 1.0
                        else:
                            secondary_score += 0.5  # Each matching secondary skill adds 0.5
        
        # Cap secondary score at 1.0
        secondary_score = min(secondary_score, 1.0)
        
        return {
            "primary": primary_score,
            "secondary": secondary_score
        }

    def _score_equipment(self, required_equipment: List[str]) -> float:
        """Score based on whether user has all required equipment"""
        if not required_equipment:
            return 1.0  # No equipment needed is good
            
        available = set(self.preferences.available_equipment)
        required = set(required_equipment)
        
        if required.issubset(available):
            return 1.0  # Has all required equipment
        return 0.0  # Missing some equipment

    def _score_location(self, suitable_locations: List[str]) -> float:
        """Score based on location match"""
        return 1.0 if self.preferences.training_location in suitable_locations else 0.0

    def _score_difficulty(self, difficulty: str) -> float:
        """Score how well the difficulty matches user's level"""
        difficulty_levels = {"beginner": 0, "intermediate": 1, "advanced": 2}
        pref_level = difficulty_levels[self.preferences.difficulty]
        drill_level = difficulty_levels[difficulty]
        
        # Perfect match gets 1.0, one level difference gets 0.5, two levels difference gets 0
        difference = abs(pref_level - drill_level)
        return max(0.0, 1.0 - (difference * 0.5))

    def _score_intensity(self, intensity: str) -> float:
        """Score how well the intensity matches training style"""
        intensity_map = {
            "low": ["GAME_RECOVERY", "REST_DAY"],
            "medium": ["MEDIUM_INTENSITY", "GAME_PREP"],
            "high": ["HIGH_INTENSITY"]
        }
        
        if self.preferences.training_style in intensity_map[intensity]:
            return 1.0
        return 0.5  # Not ideal but not completely unsuitable

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

    def _score_training_style(self, suitable_styles: List[str]) -> float:
        """Score how well the drill matches the desired training style"""
        return 1.0 if self.preferences.training_style in suitable_styles else 0.0

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
    