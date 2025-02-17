from sqlalchemy.orm import Session
from models import (
    Drill, 
    TrainingSession, 
    SessionPreferences,
    TrainingLocation,
    TrainingStyle,
    Difficulty
)
from typing import List
from utils.drill_scorer import DrillScorer

class SessionGenerator:
    def __init__(self, db: Session):
        self.db = db

    async def generate_session(self, preferences: SessionPreferences) -> TrainingSession:
        """Generate a training session based on user preferences"""
        # Get all drills from database
        all_drills = self.db.query(Drill).all()
        print(f"\nFound {len(all_drills)} total drills")

        # Create drill scorer that scores drills based on user preferences
        scorer = DrillScorer(preferences)
        
        # Score and rank all drills
        ranked_drills = scorer.rank_drills(all_drills)
        
        # Filter suitable drills
        suitable_drills = []
        current_duration = 0

        # Filter drills based on user preferences and scores
        for ranked_drill in ranked_drills:
            drill = ranked_drill['drill']
            scores = ranked_drill['scores']
            
            print(f"\nChecking drill: {drill.title}")
            print(f"Total score: {ranked_drill['total_score']}")
            print(f"Score breakdown: {scores}")
            
            # Skip drills with zero scores in critical areas
            if scores['equipment'] == 0 or scores['location'] == 0:
                print("❌ Failed critical requirements check")
                continue
                
            # Skip drills with very low skill relevance
            if scores['primary_skill'] == 0 and scores['secondary_skill'] == 0:
                print("❌ Failed skill relevance check")
                continue

            # Calculate intensity modifier based on player level vs drill difficulty
            intensity_modifier = self._calculate_intensity_modifier(preferences.difficulty, drill.difficulty)
            
            # Adjust drill duration based on session time constraint
            original_duration = drill.duration
            adjusted_duration = self._adjust_duration_for_session_fit(
                original_duration, 
                preferences.duration,
                current_duration,
                len(suitable_drills)
            )

            print(f"Original duration: {original_duration} minutes")
            print(f"Adjusted duration: {adjusted_duration} minutes")

            # Store the adjustments with the drill
            drill.adjusted_duration = adjusted_duration
            drill.intensity_modifier = intensity_modifier
            drill.original_duration = original_duration

            # Add drill to suitable drills
            suitable_drills.append(drill)
            current_duration += adjusted_duration

            # If we've significantly exceeded the preferred duration, stop adding drills
            if current_duration > preferences.duration * 1.2:  # Allow 20% overflow before stopping
                break

        print(f"\nFound {len(suitable_drills)} suitable drills")

        # Normalize durations to fit within target time
        if suitable_drills:
            suitable_drills = self._normalize_session_duration(suitable_drills, preferences.duration)
            current_duration = sum(drill.adjusted_duration for drill in suitable_drills)

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

    def _adjust_duration_for_session_fit(
        self, 
        original_duration: int, 
        target_session_duration: int,
        current_session_duration: int,
        num_drills_so_far: int
    ) -> int:
        """
        Adjust drill duration to better fit within session constraints while maintaining effectiveness.
        Uses a dynamic approach based on session progress and remaining time.
        """
        # If this is the first drill, aim for about 25-35% of session time
        if num_drills_so_far == 0:
            target_first_drill = target_session_duration * 0.3  # 30% of session time
            return max(int(min(original_duration, target_first_drill)), 5)  # minimum 5 minutes

        # Calculate remaining session time
        remaining_time = target_session_duration - current_session_duration

        # If we have plenty of time, keep original duration
        if remaining_time > original_duration * 1.5:
            return original_duration

        # If we're running short on time, scale duration down
        # but maintain a minimum effective duration
        min_effective_duration = max(5, int(original_duration * 0.6))  # minimum 60% of original or 5 minutes
        scaled_duration = min(original_duration, int(remaining_time * 0.7))  # take up to 70% of remaining time
        
        return max(min_effective_duration, scaled_duration)

    def _normalize_session_duration(self, drills: List[Drill], target_duration: int) -> List[Drill]:
        """
        Normalize drill durations to fit within target session duration by proportionally
        reducing all drill durations while maintaining minimum effective durations.
        """
        current_duration = sum(drill.adjusted_duration for drill in drills)
        
        if current_duration <= target_duration:
            return drills
        
        # Calculate the reduction ratio needed
        reduction_ratio = target_duration / current_duration
        
        # Keep track of total reduction and remaining drills to adjust
        total_adjusted = 0
        
        # First pass: Try to reduce all drills proportionally
        for drill in drills:
            # Calculate new duration with ratio, ensuring minimum of 5 minutes
            new_duration = max(5, int(drill.adjusted_duration * reduction_ratio))
            drill.adjusted_duration = new_duration
            total_adjusted += new_duration
        
        # Second pass: If we're still over, reduce longer drills more aggressively
        if total_adjusted > target_duration:
            excess_time = total_adjusted - target_duration
            drills_by_duration = sorted(drills, key=lambda x: x.adjusted_duration, reverse=True)
            
            for drill in drills_by_duration:
                if excess_time <= 0:
                    break
                
                # Calculate how much we can reduce this drill
                current_duration = drill.adjusted_duration
                min_duration = max(5, int(drill.original_duration * 0.4))  # Allow up to 60% reduction
                potential_reduction = current_duration - min_duration
                
                if potential_reduction > 0:
                    # Reduce by either the excess time or the potential reduction
                    actual_reduction = min(excess_time, potential_reduction)
                    drill.adjusted_duration = current_duration - actual_reduction
                    excess_time -= actual_reduction
        
        return drills