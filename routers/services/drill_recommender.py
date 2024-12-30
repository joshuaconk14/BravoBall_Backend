from sqlalchemy.orm import Session
from models import Drill, User
from typing import List
import numpy as np

class DrillRecommender:
    def __init__(self, db: Session):
        self.db = db

    def get_recommendations(self, user: User, limit: int = 3) -> List[Drill]:
        # Get all drills
        drills = self.db.query(Drill).all()

        # TODO make this recommendation system better
        # Calculate scores for each drill based on user's preferences
        scored_drills = []
        for drill in drills:
            score = self._calculate_drill_score(drill, user)
            scored_drills.append((drill, score))

        scored_drills.sort(key=lambda x: x[1], reverse=True)
        return [drill for drill, _ in scored_drills[:limit]]
    
    # TODO make score calculation better
    def _calculate_drill_score(self, drill: Drill, user: User) -> float:
        score = 0.0
        
        # Match difficulty level
        difficulty_map = {"Beginner": 1, "Intermediate": 2, "Advanced": 3}
        user_level = difficulty_map.get(user.skill_level, 2)
        drill_level = difficulty_map.get(drill.difficulty, 2)
        score += (1 - abs(user_level - drill_level) * 0.3)  # Smaller difference is better
        
        # Position matching
        if user.position in drill.recommended_positions:
            score += 0.3
            
        # Primary goal matching
        if user.primary_goal.lower() in [focus.lower() for focus in drill.skill_focus]:
            score += 0.4
        
        # TODO add equipment availability into frontend
        # Equipment availability (if we had this info)
        # score += equipment_match_score * 0.2
        
        return score