"""
This file is used to seed the database with drills.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, DrillCategory, Drill
from db import SQLALCHEMY_DATABASE_URL
from test_drills import drills

def seed_drills():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Create categories
        categories = [
            DrillCategory(name="Dribbling", description="Drills focused on ball control and dribbling skills"),
            DrillCategory(name="Shooting", description="Drills to improve shooting accuracy and power"),
            DrillCategory(name="Passing", description="Drills for passing accuracy and technique"),
            DrillCategory(name="First Touch", description="Drills to improve ball reception and control"),
            DrillCategory(name="Physical", description="Drills for improving speed, agility, and stamina")
        ]

        # Add categories
        for category in categories:
            existing = db.query(DrillCategory).filter_by(name=category.name).first()
            if not existing:
                db.add(category)
        db.commit()

        # Add drills
        for drill_data in drills:
            category = db.query(DrillCategory).filter_by(name=drill_data["category"]).first()
            if category:
                existing = db.query(Drill).filter_by(title=drill_data["title"]).first()
                if existing:
                    # Update existing drill
                    existing.recommended_positions = drill_data.get("recommended_positions", [])
                    existing.skill_focus = drill_data.get("skill_focus", [])
                    db.merge(existing)
                else:
                    # Create new drill
                    drill = Drill(
                        category_id=category.id,
                        title=drill_data["title"],
                        description=drill_data["description"],
                        duration=drill_data["duration"],
                        difficulty=drill_data["difficulty"],
                        recommended_equipment=drill_data["equipment"],
                        instructions=drill_data["instructions"],
                        tips=drill_data["tips"],
                        video_url=drill_data["video_url"],
                        recommended_positions=drill_data.get("recommended_positions", []),
                        skill_focus=drill_data.get("skill_focus", [])
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