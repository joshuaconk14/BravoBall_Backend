# """
# This file contains the DrillRecommender class, which is used to recommend drills to users based on their preferences.
# """

# from sqlalchemy.orm import Session
# from models import Drill, User
# from typing import List
# import numpy as np

# class DrillRecommender:
#     def __init__(self, db: Session):
#         self.db = db

#     def get_recommendations(self, user: User, limit: int = 3) -> List[tuple]:
#         # Get all drills
#         drills = self.db.query(Drill).all()

#         # TODO make this recommendation system better
#         # Calculate scores for each drill based on user's preferences
#         scored_drills = []
#         for drill in drills:
#             score = self._calculate_drill_score(drill, user)
#             scored_drills.append((drill, score))

#         scored_drills.sort(key=lambda x: x[1], reverse=True)
#         return scored_drills[:limit]  # Return tuples of (drill, score)
    
#     # TODO make score calculation better
#     def _calculate_drill_score(self, drill: Drill, user: User) -> float:
#         score = 0.0
        
#         # Match difficulty level
#         difficulty_map = {
#             "Beginner": 1,
#             "Intermediate": 2,
#             "Competitive": 3,
#             "Professional": 4
#         }

#         user_level = difficulty_map.get(user.skill_level, 2)
#         drill_level = difficulty_map.get(drill.difficulty, 2)
#         score += (1 - abs(user_level - drill_level) * 0.3)  # Smaller difference is better
        
#         # Position matching
#         if user.position in drill.recommended_positions:
#             score += 0.3
            
#         # Primary goal matching
#         if user.primary_goal.lower() in [focus.lower() for focus in drill.skill_focus]:
#             score += 0.4
        
#         # Equipment availability check
#         recommended_equipment = set(drill.recommended_equipment)
#         available_equipment = set(user.available_equipment)
#         if recommended_equipment.issubset(available_equipment):
#             score += 0.3  # Full equipment bonus
#         else:
#             # Partial equipment match
#             equipment_match_ratio = len(recommended_equipment.intersection(available_equipment)) / len(recommended_equipment)
#             score += equipment_match_ratio * 0.15
        
#         return score