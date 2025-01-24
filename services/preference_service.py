from datetime import datetime, UTC
from models import *
from sqlalchemy.orm import Session

class PreferenceService:
    @staticmethod
    def create_initial_preferences(db: Session, user_id: int, onboarding_data: OnboardingData) -> SessionPreferences:
        """Convert onboarding data into initial session preferences"""
        
        # Map experience level to training style
        training_style_map = {
            ExperienceLevel.BEGINNER: TrainingStyle.MEDIUM_INTENSITY,
            ExperienceLevel.INTERMEDIATE: TrainingStyle.MEDIUM_INTENSITY,
            ExperienceLevel.ADVANCED: TrainingStyle.HIGH_INTENSITY,
            ExperienceLevel.PROFESSIONAL: TrainingStyle.HIGH_INTENSITY
        }

        # Convert training duration to minutes
        duration_map = {
            TrainingDuration.MINS_15: 15,
            TrainingDuration.MINS_30: 30,
            TrainingDuration.MINS_45: 45,
            TrainingDuration.MINS_60: 60,
            TrainingDuration.MINS_90: 90,
            TrainingDuration.MINS_120: 120
        }

        prefs = SessionPreferences(
            user_id=user_id,
            duration=duration_map[onboarding_data.daily_training_time],
            equipment=[eq.value for eq in onboarding_data.available_equipment],
            training_style=training_style_map[onboarding_data.experience_level].value,
            location=onboarding_data.training_location.value,
            difficulty=onboarding_data.experience_level.value,
            target_skills=[skill.value for skill in onboarding_data.areas_to_improve],
            created_at=datetime.now(UTC)
        )

        db.add(prefs)
        db.commit()
        db.refresh(prefs)
        return prefs 