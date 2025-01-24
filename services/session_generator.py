from sqlalchemy import func
from typing import List
from models import *
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

class SessionGenerator:
    def __init__(self, db: Session):
        self.db = db

    def _filter_drills(self, preferences: SessionPreferences) -> List[Drill]:
        """Filter drills based on session preferences"""
        query = self.db.query(Drill)

        # Basic filters using PostgreSQL JSONB operators
        query = query.filter(
            # Check if user has the required equipment
            func.cast(Drill.required_equipment, JSONB).contained_by(
                func.cast(preferences.equipment, JSONB)
            ),
            # Match location
            func.cast(Drill.suitable_locations, JSONB).contains(preferences.location),
            # Match any of the target skills
            func.cast(Drill.skill_focus, JSONB).contains(preferences.target_skills[0])
        )

        if preferences.difficulty:
            query = query.filter(Drill.difficulty == preferences.difficulty)

        return query.all()

    async def generate_session(self, user: User, preferences: SessionPreferences) -> TrainingSession:
        """Generate a training session based on preferences"""
        available_drills = self._filter_drills(preferences)
        if not available_drills:
            raise ValueError("No suitable drills found for given preferences")

        # Select drills that fit within the time limit
        selected_drills = []
        total_duration = 0

        for drill in available_drills:
            if total_duration + drill.duration <= preferences.duration:
                selected_drills.append(drill)
                total_duration += drill.duration

            if total_duration >= preferences.duration:
                break

        # Create session drills
        session_drills = [
            SessionDrill(
                title=drill.title,
                sets=drill.default_sets or 3,
                reps=drill.default_reps or 8,
                duration=drill.duration,
                type=drill.drill_type,
                difficulty=drill.difficulty,
                equipment=drill.required_equipment,
                instructions=drill.instructions,
                tips=drill.tips
            )
            for drill in selected_drills
        ]

        return TrainingSession(
            total_duration=total_duration,
            drills=session_drills,
            focus_areas=preferences.target_skills
        ) 