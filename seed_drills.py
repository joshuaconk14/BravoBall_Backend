"""
This file is used to seed the database with drills.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, DrillCategory, Drill, DrillSkillFocus, SkillCategory
from db import SQLALCHEMY_DATABASE_URL
from sample_drills import sample_drills

def seed_drills():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Create categories
        categories = [
            DrillCategory(name=SkillCategory.PASSING.value, description="Drills for passing accuracy and technique"),
            DrillCategory(name=SkillCategory.SHOOTING.value, description="Drills to improve shooting accuracy and power"),
            DrillCategory(name=SkillCategory.DRIBBLING.value, description="Drills focused on ball control and dribbling skills"),
            DrillCategory(name=SkillCategory.FIRST_TOUCH.value, description="Drills to improve ball reception and control"),
            DrillCategory(name=SkillCategory.FITNESS.value, description="Drills for improving speed, agility, and stamina")
        ]

        # Add categories
        for category in categories:
            existing = db.query(DrillCategory).filter_by(name=category.name).first()
            if not existing:
                db.add(category)
        db.commit()

        # Add drills
        for drill_data in sample_drills:
            # Get primary skill category
            primary_skill = next(skill for skill in drill_data["skill_focus"] if skill["is_primary"])
            category = db.query(DrillCategory).filter_by(name=primary_skill["category"]).first()

            if category:
                existing = db.query(Drill).filter_by(title=drill_data["title"]).first()
                if existing:
                    # Update existing drill
                    for key, value in drill_data.items():
                        if key != "skill_focus":  # Handle skill focus separately
                            setattr(existing, key, value)
                    
                    # Update skill focus
                    db.query(DrillSkillFocus).filter_by(drill_id=existing.id).delete()
                    for skill in drill_data["skill_focus"]:
                        skill_focus = DrillSkillFocus(
                            drill_id=existing.id,
                            category=skill["category"],
                            sub_skill=skill["sub_skill"],
                            is_primary=skill["is_primary"]
                        )
                        db.add(skill_focus)
                    
                    db.merge(existing)
                else:
                    # Create new drill
                    drill = Drill(
                        category_id=category.id,
                        title=drill_data["title"],
                        description=drill_data["description"],
                        duration=drill_data["duration"],
                        intensity_level=drill_data["intensity_level"],
                        suitable_training_styles=drill_data["suitable_training_styles"],
                        drill_type=drill_data["drill_type"],
                        default_sets=drill_data.get("default_sets"),
                        default_reps=drill_data.get("default_reps"),
                        default_duration=drill_data.get("default_duration"),
                        rest_between_sets=drill_data.get("rest_between_sets"),
                        equipment=drill_data.get("required_equipment", []),
                        suitable_locations=drill_data.get("suitable_locations", []),
                        difficulty=drill_data.get("difficulty", "beginner"),
                        instructions=drill_data.get("instructions", []),
                        tips=drill_data.get("tips", []),
                        variations=drill_data.get("variations", [])
                    )
                    db.add(drill)
                    db.flush()  # Get the drill ID

                    # Add skill focus relationships
                    for skill in drill_data["skill_focus"]:
                        skill_focus = DrillSkillFocus(
                            drill_id=drill.id,
                            category=skill["category"],
                            sub_skill=skill["sub_skill"],
                            is_primary=skill["is_primary"]
                        )
                        db.add(skill_focus)

        db.commit()
        print("Successfully seeded drill categories and drills!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding drills: {str(e)}")
        raise  # Re-raise the exception to see the full traceback
    finally:
        db.close()

if __name__ == "__main__":
    seed_drills()