from sqlalchemy.orm import Session
from models import Drill, TrainingSession, SessionPreferences, SessionDrill

class SessionGenerator:
    def __init__(self, db: Session):
        self.db = db

    async def generate_session(self, preferences: SessionPreferences) -> TrainingSession:
        """Generate a training session based on user preferences"""
        
        # Get all drills
        all_drills = self.db.query(Drill).all()
        print(f"\nFound {len(all_drills)} total drills")
        
        # Filter drills based on preferences
        suitable_drills = []
        for drill in all_drills:
            # Debug print
            print(f"\nChecking drill: {drill.title}")
            print(f"Required equipment: {drill.required_equipment}")
            print(f"Available equipment: {preferences.available_equipment}")
            print(f"Location: {drill.suitable_locations}")
            print(f"Preferred location: {preferences.location}")
            print(f"Difficulty: {drill.difficulty}")
            print(f"Preferred difficulty: {preferences.difficulty}")
            
            # Check equipment
            required_equipment = set(drill.required_equipment)
            available_equipment = set(preferences.available_equipment)
            if not required_equipment.issubset(available_equipment):
                print("❌ Failed equipment check")
                continue
                
            # Check location
            if preferences.location not in drill.suitable_locations:
                print("❌ Failed location check")
                continue
                
            # Check difficulty
            if drill.difficulty != preferences.difficulty:
                print("❌ Failed difficulty check")
                continue
                
            print("✅ Drill matches all criteria!")
            suitable_drills.append(drill)

        print(f"\nFound {len(suitable_drills)} suitable drills")
        
        # Create session with filtered drills
        session = TrainingSession(
            drills=[
                SessionDrill(
                    title=drill.title,
                    duration=drill.duration,
                    difficulty=drill.difficulty,
                    required_equipment=drill.required_equipment,
                    suitable_locations=drill.suitable_locations,
                    instructions=drill.instructions,
                    tips=drill.tips
                ) for drill in suitable_drills
            ],
            total_duration=sum(drill.duration for drill in suitable_drills),
            focus_areas=preferences.target_skills if preferences.target_skills else []
        )

        return session