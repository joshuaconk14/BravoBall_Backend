from sqlalchemy.orm import Session
from models import Drill, TrainingSession, SessionPreferences

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
            print(f"Training location: {drill.suitable_locations}")
            print(f"Preferred training location: {preferences.training_location}")
            print(f"Difficulty: {drill.difficulty}")
            print(f"Preferred difficulty: {preferences.difficulty}")
            
            # Check equipment
            required_equipment = set(drill.required_equipment)
            available_equipment = set(preferences.available_equipment)
            if not required_equipment.issubset(available_equipment):
                print("❌ Failed equipment check")
                continue
                
            # Check training location
            if preferences.training_location not in drill.suitable_locations:
                print("❌ Failed training location check")
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
            total_duration=sum(drill.duration for drill in suitable_drills),
            drills=suitable_drills,
            focus_areas=preferences.target_skills if preferences.target_skills else []
        )

        # Add to database if user is provided
        if preferences.user_id:
            session.user_id = preferences.user_id
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)

        return session