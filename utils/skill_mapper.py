"""
Skill Mapper Utility

This module provides functions to map between frontend display skills and backend skill identifiers.
It maintains consistency between the frontend and backend skill representations.
"""

from typing import Set, Dict, List

# Frontend to backend skill mapping
SKILL_MAP: Dict[str, str] = {
    # Dribbling
    "Close control": "dribbling-close_control",
    "Speed dribbling": "dribbling-speed_dribbling",
    "1v1 moves": "dribbling-1v1_moves",
    "Change of direction": "dribbling-change_of_direction",
    "Ball mastery": "dribbling-ball_mastery",
    
    # First Touch
    "Ground control": "first_touch-ground_control",
    "Aerial control": "first_touch-aerial_control",
    "Turn with ball": "first_touch-turn_with_ball",
    "Touch and move": "first_touch-touch_and_move",
    "Juggling": "first_touch-juggling",
    
    # Passing
    "Short passing": "passing-short_passing",
    "Long passing": "passing-long_passing",
    "One touch passing": "passing-one_touch_passing",
    "Technique": "passing-technique",
    "Passing with movement": "passing-passing_with_movement",
    
    # Shooting
    "Power shots": "shooting-power_shots",
    "Finesse shots": "shooting-finesse_shots",
    "First time shots": "shooting-first_time_shots",
    "1v1 to shoot": "shooting-1v1_to_shoot",
    "Shooting on the run": "shooting-shooting_on_the_run",
    "Volleying": "shooting-volleying",
    
    # Defending
    "Tackling": "defending-tackling",
    "Marking": "defending-marking",
    "Intercepting": "defending-intercepting",
    "Positioning": "defending-positioning"
}

# Reverse mapping for backend to frontend
REVERSE_SKILL_MAP: Dict[str, str] = {v: k for k, v in SKILL_MAP.items()}

def map_frontend_to_backend(display_skills: Set[str]) -> Set[str]:
    """
    Map frontend display skills to backend skill identifiers.
    
    Args:
        display_skills: Set of frontend display skill names
        
    Returns:
        Set of backend skill identifiers
    """
    return {SKILL_MAP[skill] for skill in display_skills if skill in SKILL_MAP}

def map_backend_to_frontend(backend_skills: Set[str]) -> Set[str]:
    """
    Map backend skill identifiers to frontend display skills.
    
    Args:
        backend_skills: Set of backend skill identifiers
        
    Returns:
        Set of frontend display skill names
    """
    return {REVERSE_SKILL_MAP[skill] for skill in backend_skills if skill in REVERSE_SKILL_MAP}

def format_skills_for_session(skills: Set[str]) -> List[Dict[str, List[str]]]:
    """
    Format skills for session preferences in the required structure.
    
    Args:
        skills: Set of backend skill identifiers
        
    Returns:
        List of dictionaries with category and sub_skills
    """
    # Group skills by category
    categories: Dict[str, List[str]] = {}
    for skill in skills:
        category, sub_skill = skill.split('-')
        if category not in categories:
            categories[category] = []
        categories[category].append(sub_skill)
    
    # Format into required structure
    return [{"category": category, "sub_skills": sub_skills} 
            for category, sub_skills in categories.items()] 