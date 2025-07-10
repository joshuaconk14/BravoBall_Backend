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