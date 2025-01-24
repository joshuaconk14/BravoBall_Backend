"""
This file is used to seed the database with drills.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, DrillCategory, Drill
from db import SQLALCHEMY_DATABASE_URL
from sample_drills import sample_drills

def seed_drills():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Create categories
        categories = [
            DrillCategory(name="Passing", description="Drills for passing accuracy and technique"),
            DrillCategory(name="Shooting", description="Drills to improve shooting accuracy and power"),
            DrillCategory(name="Dribbling", description="Drills focused on ball control and dribbling skills"),
            DrillCategory(name="First Touch", description="Drills to improve ball reception and control"),
            DrillCategory(name="Physical", description="Drills for improving speed, agility, and stamina")
        ]

        # Add categories
        for category in categories:
            existing = db.query(DrillCategory).filter_by(name=category.name).first()
            if not existing:
                db.add(category)
        db.commit()

        # Map drill types to categories
        category_map = {
            "short_passing": "Passing",
            "power_shots": "Shooting",
            "speed_dribbling": "Dribbling"
        }

        # Add drills
        for drill_data in sample_drills:
            # Determine category based on first skill focus
            primary_skill = drill_data["skill_focus"][0]
            category_name = category_map.get(primary_skill, "Physical")
            category = db.query(DrillCategory).filter_by(name=category_name).first()

            if category:
                existing = db.query(Drill).filter_by(title=drill_data["title"]).first()
                if existing:
                    # Update existing drill
                    for key, value in drill_data.items():
                        setattr(existing, key, value)
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
                        required_equipment=drill_data["required_equipment"],
                        suitable_locations=drill_data["suitable_locations"],
                        difficulty=drill_data["difficulty"],
                        skill_focus=drill_data["skill_focus"],
                        instructions=drill_data["instructions"],
                        tips=drill_data["tips"],
                        variations=drill_data.get("variations", [])
                    )
                    db.add(drill)

        db.commit()
        print("Successfully seeded drill categories and drills!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding drills: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_drills()