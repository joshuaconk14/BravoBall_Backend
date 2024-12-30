"""
This file is used to seed the database with drills.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, DrillCategory, Drill
from db import SQLALCHEMY_DATABASE_URL

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

        # Extended list of drills
        drills = [
            {
                "category": "Dribbling",
                "title": "Cone Weaving",
                "description": "Improve close control and change of direction",
                "duration": 15,
                "difficulty": "Beginner",
                "equipment": ["cones", "ball"],
                "instructions": [
                    "Set up 6 cones in a straight line, 2 yards apart",
                    "Dribble through cones using inside and outside of foot",
                    "Return to start and repeat with other foot",
                    "Gradually increase speed while maintaining control"
                ],
                "tips": [
                    "Keep the ball close to your feet",
                    "Use both feet",
                    "Look up occasionally while dribbling"
                ],
                "video_url": "https://youtube.com/example1"
            },
            {
                "category": "Shooting",
                "title": "Power Shot Practice",
                "description": "Develop shooting power and accuracy",
                "duration": 20,
                "difficulty": "Advanced",
                "equipment": ["balls", "goal", "cones"],
                "instructions": [
                    "Place ball 20 yards from goal",
                    "Take 3 steps back from ball",
                    "Run up and strike through the ball",
                    "Aim for the corners of the goal"
                ],
                "tips": [
                    "Lock ankle when striking",
                    "Follow through with shooting foot",
                    "Keep head steady and eyes on ball"
                ],
                "video_url": "https://youtube.com/example2"
            },
            {
                "category": "Passing",
                "title": "Wall Pass Precision",
                "description": "Improve passing accuracy and first touch",
                "duration": 15,
                "difficulty": "Beginner",
                "equipment": ["ball", "wall"],
                "instructions": [
                    "Stand 5 yards from wall",
                    "Pass ball against wall",
                    "Control returning ball",
                    "Pass again with alternate foot"
                ],
                "tips": [
                    "Focus on passing technique",
                    "Use inside of foot",
                    "Keep passes firm but controlled"
                ],
                "video_url": "https://youtube.com/example3"
            },
            {
                "category": "First Touch",
                "title": "High Ball Control",
                "description": "Master controlling high balls",
                "duration": 25,
                "difficulty": "Intermediate",
                "equipment": ["balls"],
                "instructions": [
                    "Throw ball high in the air",
                    "Control with different body parts",
                    "Keep ball close after control",
                    "Progress to partner throws"
                ],
                "tips": [
                    "Relax body part receiving ball",
                    "Watch ball all the way down",
                    "Cushion the ball on contact"
                ],
                "video_url": "https://youtube.com/example4"
            },
            {
                "category": "Physical",
                "title": "Agility Ladder Sprint",
                "description": "Enhance footwork and speed",
                "duration": 20,
                "difficulty": "Intermediate",
                "equipment": ["agility ladder", "cones"],
                "instructions": [
                    "Set up agility ladder",
                    "Perform quick feet patterns",
                    "Sprint 10 yards after ladder",
                    "Walk back and repeat"
                ],
                "tips": [
                    "Stay on balls of feet",
                    "Pump arms while running",
                    "Keep head up and balanced"
                ],
                "video_url": "https://youtube.com/example5"
            },
            {
                "category": "Dribbling",
                "title": "1v1 Mirror Drill",
                "description": "Improve dribbling under pressure",
                "duration": 15,
                "difficulty": "Advanced",
                "equipment": ["ball", "cones"],
                "instructions": [
                    "Work with partner in confined space",
                    "One player leads with ball",
                    "Other player mirrors movement",
                    "Switch roles after 2 minutes"
                ],
                "tips": [
                    "Use quick changes of direction",
                    "Keep ball under close control",
                    "Practice deceptive movements"
                ],
                "video_url": "https://youtube.com/example6"
            },
            {
                "category": "Shooting",
                "title": "One-Touch Finishing",
                "description": "Improve quick shooting ability",
                "duration": 30,
                "difficulty": "Advanced",
                "equipment": ["balls", "goal", "passing partner"],
                "instructions": [
                    "Position yourself near penalty spot",
                    "Partner serves balls from different angles",
                    "Strike first-time towards goal",
                    "Vary service height and speed"
                ],
                "tips": [
                    "Keep body over the ball",
                    "Select target before ball arrives",
                    "Focus on clean contact"
                ],
                "video_url": "https://youtube.com/example7"
            },
            {
                "category": "Passing",
                "title": "Triangle Passing",
                "description": "Develop passing accuracy and movement",
                "duration": 20,
                "difficulty": "Intermediate",
                "equipment": ["balls", "cones"],
                "instructions": [
                    "Set up three cones in triangle",
                    "One player at each cone",
                    "Pass and follow your pass",
                    "One-touch passing when comfortable"
                ],
                "tips": [
                    "Communicate with teammates",
                    "Move quickly after passing",
                    "Keep passes on ground"
                ],
                "video_url": "https://youtube.com/example8"
            },
            {
                "category": "First Touch",
                "title": "Volley Control Circuit",
                "description": "Master controlling volleys",
                "duration": 25,
                "difficulty": "Advanced",
                "equipment": ["balls", "cones"],
                "instructions": [
                    "Partner serves volleyed passes",
                    "Control with designated surface",
                    "Keep ball within control zone",
                    "Progress to moving control"
                ],
                "tips": [
                    "Watch ball carefully",
                    "Select controlling surface early",
                    "Create cushioned surface"
                ],
                "video_url": "https://youtube.com/example9"
            },
            {
                "category": "Physical",
                "title": "Box-to-Box Sprints",
                "description": "Build stamina and speed",
                "duration": 20,
                "difficulty": "Advanced",
                "equipment": ["cones"],
                "instructions": [
                    "Mark out 50-yard distance",
                    "Sprint full distance",
                    "Jog back recovery",
                    "Repeat 8-10 times"
                ],
                "tips": [
                    "Maintain proper running form",
                    "Focus on breathing rhythm",
                    "Push through fatigue safely"
                ],
                "video_url": "https://youtube.com/example10"
            }
        ]

        # Add drills
        for drill_data in drills:
            category = db.query(DrillCategory).filter_by(name=drill_data["category"]).first()
            if category:
                drill = Drill(
                    category_id=category.id,
                    title=drill_data["title"],
                    description=drill_data["description"],
                    duration=drill_data["duration"],
                    difficulty=drill_data["difficulty"],
                    equipment=drill_data["equipment"],
                    instructions=drill_data["instructions"],
                    tips=drill_data["tips"],
                    video_url=drill_data["video_url"]
                )
                existing = db.query(Drill).filter_by(title=drill.title).first()
                if not existing:
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