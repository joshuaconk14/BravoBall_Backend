"""
Session Generator Module

This module is responsible for generating personalized training sessions based on user preferences.
It uses an intelligent scoring system to select and adapt drills that match the user's needs,
equipment availability, and skill level.

Key features:
- Smart drill selection based on multiple criteria
- Duration adjustment to fit session constraints
- Equipment availability validation
- Skill relevance scoring
- Intensity modification based on player level
"""

from sqlalchemy.orm import Session
from models import (
    Drill, 
    TrainingSession, 
    SessionPreferences,
    TrainingLocation,
    TrainingStyle,
    Difficulty,
    OrderedSessionDrill
)
from typing import List, Dict
from utils.drill_scorer import DrillScorer
from config import get_logger

logger = get_logger(__name__)

class SessionGenerator:
    """
    Generates personalized training sessions based on user preferences and available drills.
    
    Attributes:
        ADAPTABLE_EQUIPMENT: Equipment that can be substituted with household items
        CRITICAL_EQUIPMENT: Essential equipment that cannot be easily substituted
        BASIC_SKILLS: Fundamental skills that can be practiced with minimal equipment
    """

    # Mapping from duration to max drills
    DURATION_TO_MAX_DRILLS = {
        15: 2,
        30: 3,
        45: 4,
        60: 5,
        90: 6,
        120: 7,
    }

    def __init__(self, db: Session):
        """Initialize the session generator with a database connection."""
        self.db = db
        self.ADAPTABLE_EQUIPMENT = {"CONES", "WALL"}  # Can use household items instead
        self.CRITICAL_EQUIPMENT = {"GOALS", "BALL"}   # Essential equipment
        self.BASIC_SKILLS = {"passing", "shooting", "first_touch", "dribbling", "defending", "goalkeeping", "fitness"}  # Core skills including goalkeeping and fitness

    async def generate_session(self, preferences: SessionPreferences) -> TrainingSession:
        """
        Generate a training session based on user preferences.
        
        Args:
            preferences: User's session preferences including duration, equipment, etc.
            
        Returns:
            A TrainingSession object containing selected and adjusted drills.
            
        The generation process involves:
        1. Retrieving and scoring all available drills
        2. Creating a larger pool of top-ranked drills
        3. Balancing drill selection to match user's skill preferences proportionally
        4. Adjusting drill durations to fit session constraints
        5. Normalizing the overall session duration
        """
        # Get and rank all available drills
        all_drills = self.db.query(Drill).all()
        logger.info(f"\nFound {len(all_drills)} total drills")

        scorer = DrillScorer(preferences)
        ranked_drills = scorer.rank_drills(all_drills)
        
        # Determine max drills for this session duration
        max_drills = self.DURATION_TO_MAX_DRILLS.get(preferences.duration, 4)
        
        # Create a larger pool for skill balancing (4-5x the target number)
        pool_size = min(len(ranked_drills), max_drills * 5)
        drill_pool = ranked_drills[:pool_size]
        
        logger.info(f"Created drill pool of {pool_size} drills from {len(ranked_drills)} total ranked drills")
        
        # Balance drill selection based on user's skill preferences
        selected_drills = self._balance_drill_selection_by_skills(drill_pool, max_drills, preferences)
        
        logger.info(f"Selected {len(selected_drills)} balanced drills for session")

        suitable_drills = []
        current_duration = 0
        has_limited_equipment = len(preferences.available_equipment) <= 1

        # Process the balanced selection of drills
        for ranked_drill in selected_drills:
            drill = ranked_drill['drill']
            scores = ranked_drill['scores']
            
            logger.info(f"\nProcessing drill: {drill.title}")
            logger.info(f"Score: {ranked_drill['total_score']:.2f}")
            logger.info(f"Primary skill: {self._get_drill_primary_skill(drill)}")

            # Adjust drill duration based on session constraints
            adjusted_duration = self._adjust_drill_duration(
                drill, 
                preferences.duration,
                current_duration,
                len(suitable_drills),
                has_limited_equipment
            )

            logger.info(f"Original duration: {drill.duration} minutes")
            logger.info(f"Adjusted duration: {adjusted_duration} minutes")

            # Store drill adjustments
            drill.adjusted_duration = adjusted_duration
            drill.intensity_modifier = self._calculate_intensity_modifier(preferences.difficulty, drill.difficulty)
            drill.original_duration = drill.duration if drill.duration is not None else adjusted_duration

            suitable_drills.append(drill)
            current_duration += adjusted_duration

        # If total duration > session time, drop drills from the end until it fits
        while sum(drill.adjusted_duration for drill in suitable_drills) > preferences.duration and len(suitable_drills) > 1:
            removed = suitable_drills.pop()
            logger.warning(f"Removed drill '{removed.title}' to fit session duration constraint.")

        logger.info(f"\nFound {len(suitable_drills)} suitable drills")

        # Normalize durations to fit within target time
        if suitable_drills:
            suitable_drills = self._normalize_session_duration(suitable_drills, preferences.duration)
            current_duration = sum(drill.adjusted_duration for drill in suitable_drills)

        # --- SESSION CREATION/UPDATE LOGIC ---
        # At this point, we have a list of suitable drills with per-session adjustments (duration, etc.)
        # We now create or update a TrainingSession and persist the per-session drill data in OrderedSessionDrill
        session = None
        if preferences.user_id:
            # Try to find an existing session for this user
            session = self.db.query(TrainingSession).filter(TrainingSession.user_id == preferences.user_id).first()
            if session:
                logger.info(f"Updating existing session for user: {preferences.user_id}")
                session.total_duration = current_duration
                session.focus_areas = preferences.target_skills
                # Remove old OrderedSessionDrills for this session (so we can add the new ones)
                self.db.query(OrderedSessionDrill).filter(OrderedSessionDrill.session_id == session.id).delete()
                self.db.commit()
            else:
                logger.info(f"Creating new session for user: {preferences.user_id}")
                session = TrainingSession(
                    total_duration=current_duration,
                    focus_areas=preferences.target_skills,
                    user_id=preferences.user_id
                )
                self.db.add(session)
                self.db.commit()
                self.db.refresh(session)
        else:
            # If no user_id, just create a session object (not persisted to a user)
            session = TrainingSession(
                total_duration=current_duration,
                focus_areas=preferences.target_skills
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)

        # --- CREATE ORDEREDSESSIONDRILL RECORDS ---
        # For each drill in the generated session, create an OrderedSessionDrill record
        # This stores the per-session, per-drill customizations (sets, reps, rest, duration, etc.)
        # and links to the static Drill for default info
        ordered_drills = []
        for idx, drill in enumerate(suitable_drills):
            osd = OrderedSessionDrill(
                session_id=session.id,  # Link to the session
                drill_id=drill.id,      # Link to the static drill
                position=idx,           # Order in the session
                sets=getattr(drill, 'sets', None),
                reps=getattr(drill, 'reps', None),
                rest=getattr(drill, 'rest', None),
                duration=getattr(drill, 'adjusted_duration', drill.duration),
                is_completed=False
            )
            self.db.add(osd)
            ordered_drills.append(osd)
        self.db.commit()
        # Attach the ordered drills to the session
        session.ordered_drills = ordered_drills
        self.db.commit()
        self.db.refresh(session)
        # Return the session with all per-session drill data attached
        return session

    def _should_stop_adding_drills(self, has_limited_equipment: bool, suitable_drills: List[Drill], 
                                 current_duration: int, target_duration: int) -> bool:
        """
        Determine if we should stop adding drills to the session.
        
        For limited equipment profiles, ensures at least 3 drills if possible.
        Otherwise, stops when reaching 120% of target duration.
        """
        if has_limited_equipment and len(suitable_drills) < 3:
            return False
        return current_duration > target_duration * 1.2

    def _adjust_drill_duration(self, drill: Drill, target_session_duration: int,
                             current_session_duration: int, num_drills_so_far: int,
                             has_limited_equipment: bool) -> int:
        """
        Adjust drill duration to fit session constraints.
        
        Args:
            drill: The drill to adjust
            target_session_duration: Desired total session duration
            current_session_duration: Current accumulated session duration
            num_drills_so_far: Number of drills already added
            has_limited_equipment: Whether the user has limited equipment
            
        Returns:
            Adjusted duration in minutes
            
        The adjustment considers:
        - Minimum effective duration (3-5 minutes)
        - First drill gets 30% of session time
        - Remaining drills are scaled based on available time
        """
        min_duration = 3 if has_limited_equipment else 5
        
        # Handle null duration with a default value
        drill_duration = drill.duration if drill.duration is not None else 10  # Default to 10 minutes if None
        
        if num_drills_so_far == 0:
            target_first_drill = target_session_duration * 0.3
            return max(int(min(drill_duration, target_first_drill)), min_duration)

        remaining_time = target_session_duration - current_session_duration
        if remaining_time > drill_duration * 1.5:
            return drill_duration

        min_effective_duration = max(min_duration, int(drill_duration * 0.6))
        scaled_duration = min(drill_duration, int(remaining_time * 0.7))
        
        return max(min_effective_duration, scaled_duration)

    def _calculate_intensity_modifier(self, player_difficulty: str, drill_difficulty: str) -> float:
        """
        Calculate intensity modifier based on player level vs drill difficulty.
        
        Returns:
            1.2: If player is more advanced than drill (increase intensity)
            1.0: If player level matches drill level
            0.8: If drill is more advanced than player (decrease intensity)
        """
        difficulty_levels = {
            "beginner": 1,
            "intermediate": 2,
            "advanced": 3
        }
        
        # Handle null values with defaults
        player_difficulty = player_difficulty.lower() if player_difficulty else "beginner"
        drill_difficulty = drill_difficulty.lower() if drill_difficulty else "beginner"
        
        # Use get() with default to handle unknown difficulty values
        player_level = difficulty_levels.get(player_difficulty, 1)  # Default to beginner
        drill_level = difficulty_levels.get(drill_difficulty, 1)    # Default to beginner
        
        level_diff = player_level - drill_level

        if level_diff > 0:
            return 1.2  # Increase intensity for more advanced players
        elif level_diff == 0:
            return 1.0  # Keep original intensity
        else:
            return 0.8  # Decrease intensity for less experienced players

    def _normalize_session_duration(self, drills: List[Drill], target_duration: int) -> List[Drill]:
        """
        Normalize drill durations to fit within target session duration.
        
        Uses a two-pass approach:
        1. Proportionally reduce all drill durations
        2. If still over target, reduce longer drills more aggressively
        
        Args:
            drills: List of drills to normalize
            target_duration: Target session duration in minutes
            
        Returns:
            List of drills with adjusted durations
        """
        # Ensure all drills have an adjusted_duration attribute
        for drill in drills:
            if not hasattr(drill, 'adjusted_duration') or drill.adjusted_duration is None:
                # Default to original duration or 10 minutes if None
                drill.adjusted_duration = drill.duration if drill.duration is not None else 10
                
        current_duration = sum(drill.adjusted_duration for drill in drills)
        if current_duration <= target_duration:
            return drills
        
        base_min_duration = max(3, min(5, target_duration // 10))
        reduction_ratio = target_duration / current_duration
        
        # First pass: proportional reduction
        total_adjusted = 0
        for drill in drills:
            new_duration = max(base_min_duration, int(drill.adjusted_duration * reduction_ratio))
            drill.adjusted_duration = new_duration
            total_adjusted += new_duration
        
        # Second pass: reduce longer drills if needed
        if total_adjusted > target_duration:
            self._reduce_longer_drills(drills, total_adjusted - target_duration, base_min_duration, target_duration)
        
        return drills

    def _reduce_longer_drills(self, drills: List[Drill], excess_time: int, base_min_duration: int, target_duration: int):
        """
        Helper method to reduce duration of longer drills.
        
        Longer sessions allow less aggressive reductions to maintain drill effectiveness.
        
        Args:
            drills: List of drills to adjust
            excess_time: Amount of time to reduce
            base_min_duration: Minimum allowed duration
            target_duration: Target session duration
        """
        drills_by_duration = sorted(drills, key=lambda x: x.adjusted_duration, reverse=True)
        # Shorter sessions allow more aggressive reduction
        max_reduction_pct = 0.8 if target_duration <= 30 else 0.7 if target_duration <= 45 else 0.6
        
        for drill in drills_by_duration:
            if excess_time <= 0:
                break
                
            current_duration = drill.adjusted_duration
            # Handle null original_duration
            original_duration = getattr(drill, 'original_duration', drill.duration)
            if original_duration is None:
                original_duration = current_duration  # Use current if original is None
                
            min_duration = max(base_min_duration, int(original_duration * (1 - max_reduction_pct)))
            potential_reduction = current_duration - min_duration
            
            if potential_reduction > 0:
                actual_reduction = min(excess_time, potential_reduction)
                drill.adjusted_duration = current_duration - actual_reduction
                excess_time -= actual_reduction

    def _balance_drill_selection_by_skills(self, drill_pool: List[Dict], max_drills: int, preferences: SessionPreferences) -> List[Dict]:
        """
        Balance drill selection to be proportional to user's selected skills.
        
        Args:
            drill_pool: List of ranked drills with scores
            max_drills: Maximum number of drills to select
            preferences: User preferences containing target skills
            
        Returns:
            List of selected drills balanced by skill distribution
        """
        if not preferences.target_skills:
            # If no specific skills selected, just return top drills
            return drill_pool[:max_drills]
        
        # Group drills by their primary skill category
        drills_by_skill = {}
        unmatched_drills = []
        
        for drill_info in drill_pool:
            primary_skill = self._get_drill_primary_skill(drill_info['drill'])
            
            if primary_skill:
                if primary_skill not in drills_by_skill:
                    drills_by_skill[primary_skill] = []
                drills_by_skill[primary_skill].append(drill_info)
            else:
                unmatched_drills.append(drill_info)
        
        # Calculate skill proportions from user's target skills
        skill_counts = self._calculate_skill_proportions(preferences.target_skills)
        total_selected_skills = sum(skill_counts.values())
        
        if total_selected_skills == 0:
            return drill_pool[:max_drills]
        
        # Allocate drills proportionally
        selected_drills = []
        allocated_count = 0
        
        for skill_category, count in skill_counts.items():
            if skill_category in drills_by_skill:
                # Calculate how many drills this skill should get
                proportion = count / total_selected_skills
                target_drills = max(1, round(proportion * max_drills))  # At least 1 drill per selected skill
                
                # Take the best drills for this skill category
                skill_drills = drills_by_skill[skill_category][:target_drills]
                selected_drills.extend(skill_drills)
                allocated_count += len(skill_drills)
                
                logger.info(f"Allocated {len(skill_drills)} drills for skill '{skill_category}' (proportion: {proportion:.2f})")
        
        # Fill remaining slots with top-scored drills if we haven't reached max_drills
        if allocated_count < max_drills:
            remaining_slots = max_drills - allocated_count
            
            # Get all drills not yet selected, sorted by score
            selected_drill_ids = {drill_info['drill'].id for drill_info in selected_drills}
            remaining_drills = [
                drill_info for drill_info in drill_pool 
                if drill_info['drill'].id not in selected_drill_ids
            ]
            
            # Add highest scoring remaining drills
            selected_drills.extend(remaining_drills[:remaining_slots])
            logger.info(f"Filled {min(remaining_slots, len(remaining_drills))} remaining slots with top-scored drills")
        
        # Sort final selection by score to maintain quality order
        selected_drills.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Ensure we don't exceed max_drills
        return selected_drills[:max_drills]

    def _get_drill_primary_skill(self, drill: Drill) -> str:
        """
        Extract the primary skill category from a drill.
        
        Args:
            drill: The drill to analyze
            
        Returns:
            Primary skill category as a string, or None if not found
        """
        if not drill.skill_focus:
            return None
            
        # Find the primary skill focus
        primary_skill = next((focus for focus in drill.skill_focus if focus.is_primary), None)
        if primary_skill and primary_skill.category:
            return primary_skill.category.lower()
            
        return None

    def _calculate_skill_proportions(self, target_skills: List) -> dict:
        """
        Calculate the proportion of each skill category from user's target skills.
        
        Args:
            target_skills: List of target skills from user preferences
            
        Returns:
            Dictionary mapping skill categories to their counts
        """
        skill_counts = {}
    
        for target in target_skills:
            if isinstance(target, dict) and "category" in target and "sub_skills" in target:
                category = target["category"].lower()
                sub_skills = target["sub_skills"]
                
                if isinstance(sub_skills, list):
                    # Count each sub-skill
                    skill_counts[category] = skill_counts.get(category, 0) + len(sub_skills)
                else:
                    # Single sub-skill
                    skill_counts[category] = skill_counts.get(category, 0) + 1
                    
                logger.info(f"Skill category '{category}' has {skill_counts[category]} sub-skills")
        
        return skill_counts