"""
Skill mapping utilities for converting between frontend display skills and backend skill identifiers.
"""

from typing import Dict, List, Set

# Mapping from display skills to backend skill identifiers
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

# Reverse mapping for converting backend identifiers to display skills
REVERSE_SKILL_MAP: Dict[str, str] = {v: k for k, v in SKILL_MAP.items()}

def map_display_to_backend_skills(display_skills: List[str]) -> List[Dict[str, List[str]]]:
    """
    Convert frontend display skills to backend skill format.
    
    Args:
        display_skills: List of display skill names (e.g., ["Close control", "Power shots"])
        
    Returns:
        List of dictionaries with category and sub_skills (e.g., 
        [{"category": "dribbling", "sub_skills": ["close_control"]}, 
         {"category": "shooting", "sub_skills": ["power_shots"]}])
    """
    # Group skills by category
    categorized_skills: Dict[str, List[str]] = {}
    
    for display_skill in display_skills:
        if display_skill in SKILL_MAP:
            backend_skill = SKILL_MAP[display_skill]
            category, sub_skill = backend_skill.split('-')
            
            if category not in categorized_skills:
                categorized_skills[category] = []
            categorized_skills[category].append(sub_skill)
    
    # Convert to required format
    return [
        {"category": category, "sub_skills": sub_skills}
        for category, sub_skills in categorized_skills.items()
    ]

def map_backend_to_display_skills(backend_skills: List[Dict[str, List[str]]]) -> List[str]:
    """
    Convert backend skill format to frontend display skills.
    
    Args:
        backend_skills: List of dictionaries with category and sub_skills
        
    Returns:
        List of display skill names
    """
    display_skills = []
    
    for skill_group in backend_skills:
        category = skill_group["category"]
        for sub_skill in skill_group["sub_skills"]:
            backend_skill = f"{category}-{sub_skill}"
            if backend_skill in REVERSE_SKILL_MAP:
                display_skills.append(REVERSE_SKILL_MAP[backend_skill])
    
    return display_skills 