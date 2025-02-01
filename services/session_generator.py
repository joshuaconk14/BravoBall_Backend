from sqlalchemy.orm import Session
from models import (
    Drill, 
    TrainingSession, 
    SessionPreferences,
    TrainingLocation,
    TrainingStyle,
    Difficulty
)

class SessionGenerator:
    def __init__(self, db: Session):
        self.db = db

    async def generate_session(self, preferences: SessionPreferences) -> TrainingSession:
        """Generate a training session based on user preferences"""
        # Get all drills from database
        all_drills = self.db.query(Drill).all()
        print(f"\nFound {len(all_drills)} total drills")

        # Filter suitable drills
        suitable_drills = []
        current_duration = 0

        # Filter drills based on user preferences
        for drill in all_drills:
            print(f"\nChecking drill: {drill.title}")
            
            # Check equipment requirements
            print(f"Required equipment: {drill.required_equipment}")
            print(f"Available equipment: {preferences.available_equipment}")
            if not all(equip in preferences.available_equipment for equip in drill.required_equipment):
                print("❌ Failed equipment check")
                continue

            # Check location suitability
            print(f"Training location: {drill.suitable_locations}")
            print(f"Preferred training location: {preferences.training_location}")
            
            # Convert stored locations to enum values for comparison
            drill_locations = [loc for loc in drill.suitable_locations]
            if preferences.training_location not in drill_locations:
                print("❌ Failed training location check")
                continue

            # Note: We no longer filter by difficulty, just print it for reference
            print(f"Difficulty: {drill.difficulty}")
            print(f"Preferred difficulty: {preferences.difficulty}")

            # Adjust intensity and reps based on player level vs drill difficulty
            intensity_modifier = self._calculate_intensity_modifier(preferences.difficulty, drill.difficulty)
            adjusted_duration = self._adjust_duration_for_difficulty(drill.duration, intensity_modifier)

            # Check if adding this drill would exceed duration limit
            if current_duration + adjusted_duration > preferences.duration:
                print("❌ Would exceed duration limit")
                continue

            print("✅ Drill matches all criteria!")
            drill.adjusted_duration = adjusted_duration  # Store adjusted duration
            drill.intensity_modifier = intensity_modifier  # Store intensity modifier
            suitable_drills.append(drill)
            current_duration += adjusted_duration

            # Stop adding drills if we've reached the duration limit
            if current_duration >= preferences.duration:
                break

        print(f"\nFound {len(suitable_drills)} suitable drills")

        # Create and return the training session
        session = TrainingSession(
            total_duration=current_duration,
            focus_areas=preferences.target_skills
        )
        session.drills = suitable_drills

        # Add to database if user is provided
        if preferences.user_id:
            session.user_id = preferences.user_id
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)

        return session

    def _calculate_intensity_modifier(self, player_difficulty: str, drill_difficulty: str) -> float:
        """Calculate intensity modifier based on player level vs drill difficulty"""
        difficulty_levels = {
            "beginner": 1,
            "intermediate": 2,
            "advanced": 3
        }
        
        player_level = difficulty_levels[player_difficulty.lower()]
        drill_level = difficulty_levels[drill_difficulty.lower()]
        level_diff = player_level - drill_level

        # If player is more advanced than drill, increase intensity
        if level_diff > 0:
            return 1.2  # 20% more intense
        # If player is at drill level, normal intensity
        elif level_diff == 0:
            return 1.0
        # If drill is more advanced than player, reduce intensity
        else:
            return 0.8  # 20% less intense

    def _adjust_duration_for_difficulty(self, base_duration: int, intensity_modifier: float) -> int:
        """Adjust drill duration based on intensity modifier"""
        # For higher intensity, we might reduce duration slightly
        if intensity_modifier > 1:
            return int(base_duration * 0.9)  # 10% shorter but more intense
        # For lower intensity, we might increase duration
        elif intensity_modifier < 1:
            return int(base_duration * 1.1)  # 10% longer but less intense
        return base_duration  # No change for matching difficulty