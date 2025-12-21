"""
treat_calculator.py
Service for calculating treat rewards based on session data.
Follows strategy pattern for different session types.
"""

from typing import Dict, Optional, Tuple
from config import get_logger

logger = get_logger(__name__)


class TreatCalculator:
    """Calculates treat rewards based on session data and user context"""
    
    def __init__(self):
        # Base treat amounts (adjusted to target ~45 treats per session)
        self.BASE_TREATS_PER_DRILL = 7  # Reduced from 10
        self.BASE_TREATS_PER_MENTAL_MINUTE = 3  # Reduced from 5
        
        # Streak multipliers
        self.STREAK_MULTIPLIERS = {
            0: 1.0,      # No streak
            1: 1.0,      # 1 day streak
            2: 1.1,      # 2 day streak
            3: 1.2,      # 3 day streak
            4: 1.3,      # 4 day streak
            5: 1.5,      # 5 day streak
            7: 2.0,      # 7 day streak
            14: 2.2,     # 14 day streak
            30: 2.5,     # 30 day streak
        }
        
        # Completion bonus (reduced to target ~45 treats per session)
        self.COMPLETION_BONUS = 12  # Bonus for completing all drills
        
        # Difficulty multipliers (bonus treats per drill based on difficulty)
        self.DIFFICULTY_BONUSES = {
            'beginner': 0,        # No bonus for beginner drills
            'intermediate': 2,    # +2 treats per intermediate drill
            'advanced': 5,        # +5 treats per advanced drill
        }
    
    def calculate_treats(
        self, 
        session_data: Dict, 
        user_context: Optional[Dict] = None
    ) -> Tuple[int, Dict]:
        """
        Calculate treats based on session data and user context.
        
        Args:
            session_data: Dictionary containing:
                - session_type: 'drill_training' or 'mental_training'
                - drills: List of drill data (for drill_training)
                - total_completed_drills: Number of completed drills
                - total_drills: Total number of drills
                - duration_minutes: Duration in minutes (for mental_training)
            user_context: Dictionary containing:
                - current_streak: Current streak count
                - previous_streak: Previous streak count
        
        Returns:
            Tuple of (treats_amount, breakdown_dict) where breakdown_dict contains:
            - drills_completed: int
            - difficulty_bonus: int
            - completion_bonus: int
            - streak_multiplier: float
            - base_treats: int
            - total_before_streak: int
        """
        session_type = session_data.get('session_type', 'drill_training')
        
        # Normalize session type - frontend may send "training" instead of "drill_training"
        if session_type in ['drill_training', 'training']:
            return self._calculate_drill_training_treats(session_data, user_context)
        elif session_type == 'mental_training':
            return self._calculate_mental_training_treats(session_data, user_context)
        else:
            # Unknown session type, return 0
            return 0, {
                'drills_completed': 0,
                'difficulty_bonus': 0,
                'completion_bonus': 0,
                'streak_multiplier': 1.0,
                'base_treats': 0,
                'total_before_streak': 0
            }
    
    def _calculate_drill_training_treats(
        self, 
        session_data: Dict, 
        user_context: Optional[Dict] = None
    ) -> Tuple[int, Dict]:
        """Calculate treats for drill training sessions"""
        total_completed_drills = session_data.get('total_completed_drills', 0)
        total_drills = session_data.get('total_drills', 0)
        drills = session_data.get('drills', [])
        
        logger.info(
            f"Calculating drill training treats: "
            f"total_drills={total_drills}, total_completed_drills={total_completed_drills}, "
            f"drills_count={len(drills)}"
        )
        
        if total_drills == 0:
            logger.warning("No drills in session, returning 0 treats")
            return 0, {
                'drills_completed': 0,
                'difficulty_bonus': 0,
                'completion_bonus': 0,
                'streak_multiplier': 1.0,
                'base_treats': 0,
                'total_before_streak': 0
            }
        
        # Base treats from completed drills
        base_treats = total_completed_drills * self.BASE_TREATS_PER_DRILL
        logger.info(f"Base treats: {base_treats} ({total_completed_drills} drills × {self.BASE_TREATS_PER_DRILL})")
        
        # Difficulty bonus (extra treats for harder drills)
        difficulty_bonus = 0
        if drills:
            for drill in drills:
                # Extract difficulty from drill data
                drill_data = drill.get('drill', drill) if isinstance(drill, dict) else drill
                if isinstance(drill_data, dict):
                    difficulty = drill_data.get('difficulty', '').lower()
                else:
                    difficulty = getattr(drill_data, 'difficulty', '').lower() if hasattr(drill_data, 'difficulty') else ''
                
                # Get bonus for this difficulty level
                bonus = self.DIFFICULTY_BONUSES.get(difficulty, 0)
                difficulty_bonus += bonus
                if bonus > 0:
                    logger.info(f"Difficulty bonus for {difficulty}: +{bonus} treats")
        
        if difficulty_bonus > 0:
            logger.info(f"Total difficulty bonus: {difficulty_bonus}")
        
        # Completion bonus (if all drills completed)
        completion_bonus = 0
        if total_completed_drills == total_drills:
            completion_bonus = self.COMPLETION_BONUS
            logger.info(f"Completion bonus: {completion_bonus}")
        
        # Calculate total before streak multiplier
        total_before_streak = base_treats + difficulty_bonus + completion_bonus
        logger.info(f"Total before streak multiplier: {total_before_streak}")
        
        # Apply streak multiplier
        streak_multiplier = self._get_streak_multiplier(user_context)
        final_treats = int(total_before_streak * streak_multiplier)
        logger.info(
            f"Final treats: {final_treats} "
            f"(streak: {user_context.get('current_streak', 0) if user_context else 0}, "
            f"multiplier: {streak_multiplier}x)"
        )
        
        # Return treats amount and breakdown
        breakdown = {
            'drills_completed': total_completed_drills,
            'difficulty_bonus': difficulty_bonus,
            'completion_bonus': completion_bonus,
            'streak_multiplier': streak_multiplier,
            'base_treats': base_treats,
            'total_before_streak': total_before_streak
        }
        
        return max(0, final_treats), breakdown  # Ensure non-negative
    
    def _calculate_mental_training_treats(
        self, 
        session_data: Dict, 
        user_context: Optional[Dict] = None
    ) -> Tuple[int, Dict]:
        """Calculate treats for mental training sessions"""
        duration_minutes = session_data.get('duration_minutes', 0)
        
        if duration_minutes <= 0:
            return 0, {
                'drills_completed': 0,
                'difficulty_bonus': 0,
                'completion_bonus': 0,
                'streak_multiplier': 1.0,
                'base_treats': 0,
                'total_before_streak': 0
            }
        
        # Base treats from duration
        base_treats = duration_minutes * self.BASE_TREATS_PER_MENTAL_MINUTE
        
        # Apply streak multiplier
        streak_multiplier = self._get_streak_multiplier(user_context)
        final_treats = int(base_treats * streak_multiplier)
        
        # Return treats amount and breakdown (mental training doesn't have drills/difficulty)
        breakdown = {
            'drills_completed': 0,
            'difficulty_bonus': 0,
            'completion_bonus': 0,
            'streak_multiplier': streak_multiplier,
            'base_treats': base_treats,
            'total_before_streak': base_treats
        }
        
        return max(0, final_treats), breakdown  # Ensure non-negative
    
    def _get_streak_multiplier(self, user_context: Optional[Dict] = None) -> float:
        """Get streak multiplier based on user's current streak"""
        if not user_context:
            return 1.0
        
        current_streak = user_context.get('current_streak', 0)
        
        # Find the highest applicable multiplier
        # Check multipliers in descending order
        for streak_threshold in sorted(self.STREAK_MULTIPLIERS.keys(), reverse=True):
            if current_streak >= streak_threshold:
                return self.STREAK_MULTIPLIERS[streak_threshold]
        
        return 1.0

