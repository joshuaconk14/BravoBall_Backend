from models import DrillSkillFocus

# Helper function to convert Drill object to DrillResponse dict
def drill_to_response(drill, db):
    # Get the primary skill
    primary_skill = db.query(DrillSkillFocus).filter(
        DrillSkillFocus.drill_id == drill.id,
        DrillSkillFocus.is_primary == True
    ).first()
    
    # Get secondary skills
    secondary_skills = db.query(DrillSkillFocus).filter(
        DrillSkillFocus.drill_id == drill.id,
        DrillSkillFocus.is_primary == False
    ).all()
    
    return {
        "uuid": str(drill.uuid),  # Use UUID as primary identifier
        "title": drill.title,
        "description": drill.description,
        "type": drill.type,
        "duration": drill.duration,
        "sets": drill.sets,
        "reps": drill.reps,
        "rest": drill.rest,
        "equipment": drill.equipment,
        "suitable_locations": drill.suitable_locations,
        "intensity": drill.intensity,
        "training_styles": drill.training_styles,
        "difficulty": drill.difficulty,
        "primary_skill": {
            "category": primary_skill.category,
            "sub_skill": primary_skill.sub_skill
        } if primary_skill else {},
        "secondary_skills": [
            {
                "category": skill.category,
                "sub_skill": skill.sub_skill
            }
            for skill in secondary_skills
        ],
        "instructions": drill.instructions,
        "tips": drill.tips,
        "common_mistakes": drill.common_mistakes,
        "progression_steps": drill.progression_steps,
        "variations": drill.variations,
        "video_url": drill.video_url,
        "thumbnail_url": drill.thumbnail_url
    }

# ✅ ADDED: Helper function to convert CustomDrill object to DrillResponse dict
def custom_drill_to_response(custom_drill):
    """
    Convert a CustomDrill object to the same response format as regular drills.
    CustomDrills store skill info as JSON, not in separate DrillSkillFocus table.
    """
    return {
        "uuid": str(custom_drill.uuid),  # Use UUID as primary identifier
        "title": custom_drill.title,
        "description": custom_drill.description,
        "type": custom_drill.type,
        "duration": custom_drill.duration,
        "sets": custom_drill.sets,
        "reps": custom_drill.reps,
        "rest": custom_drill.rest,
        "equipment": custom_drill.equipment or [],
        "suitable_locations": custom_drill.suitable_locations or [],
        "intensity": custom_drill.intensity,
        "training_styles": custom_drill.training_styles or [],
        "difficulty": custom_drill.difficulty,
        "primary_skill": custom_drill.primary_skill or {},
        "secondary_skills": custom_drill.secondary_skills or [],
        "instructions": custom_drill.instructions or [],
        "tips": custom_drill.tips or [],
        "common_mistakes": custom_drill.common_mistakes or [],
        "progression_steps": custom_drill.progression_steps or [],
        "variations": custom_drill.variations or [],
        "video_url": custom_drill.video_url,
        "thumbnail_url": custom_drill.thumbnail_url
    }

# ✅ ADDED: Universal drill converter that handles both Drill and CustomDrill objects
def any_drill_to_response(drill_object, is_custom_drill, db=None):
    """
    Convert either a Drill or CustomDrill object to response format.
    """
    if is_custom_drill:
        return custom_drill_to_response(drill_object)
    else:
        return drill_to_response(drill_object, db)