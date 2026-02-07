# my original prompt from the frontend: i want to create a dynmaic calculation in the backend that will determine how much treats the user gets after a session, what would i mneed to do for this to work. what would be good ways that would follow good swe principles and practices

# game plan:
Architecture Overview
1. Separation of Concerns
TreatCalculator: Calculates treats (separate from streak logic)
TreatRewardService: Grants treats and handles idempotency
Calculation Strategies: Different rules for different session types

# files need to implement

# app/services/treat_reward_service.py

from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.store_items import UserStoreItems  # Your existing model
from app.services.treat_calculator import TreatCalculator

class TreatRewardService:
    """Service for granting treat rewards with idempotency"""
    
    def __init__(self, db: Session):
        self.db = db
        self.calculator = TreatCalculator()
    
    def grant_session_reward(
        self,
        user: User,
        session_data: Dict,
        is_new_session: bool,  # True if session was just created, False if duplicate
        user_context: Optional[Dict] = None
    ) -> Tuple[int, bool]:
        """
        Grant treats for a completed session with idempotency.
        
        Args:
            user: The user to grant treats to
            session_data: Session data for calculation
            is_new_session: Whether this is a newly created session (False = duplicate)
            user_context: Optional user context (streak, etc.)
        
        Returns:
            Tuple of (treats_awarded, was_already_granted)
        """
        # If session already exists (duplicate), treats were already granted
        if not is_new_session:
            # Return 0 treats since this is a duplicate session
            return 0, True
        
        # Calculate treats
        treats_amount = self.calculator.calculate_treats(session_data, user_context)
        
        if treats_amount <= 0:
            return 0, False
        
        # Grant treats to user via UserStoreItems
        self._increment_user_treats(user.id, treats_amount)
        
        return treats_amount, False
    
    def _increment_user_treats(self, user_id: int, amount: int):
        """Increment user's treat balance using UserStoreItems"""
        # Get or create UserStoreItems for this user
        store_items = self.db.query(UserStoreItems).filter(
            UserStoreItems.user_id == user_id
        ).first()
        
        if not store_items:
            # Create new UserStoreItems if it doesn't exist
            store_items = UserStoreItems(
                user_id=user_id,
                treats=amount
            )
            self.db.add(store_items)
        else:
            # Increment existing treats
            store_items.treats = (store_items.treats or 0) + amount
        
        self.db.commit()
        self.db.refresh(store_items)

# app/routers/sessions.py

from app.services.treat_reward_service import TreatRewardService
from app.models.store_items import UserStoreItems

@router.post("/api/sessions/completed/", response_model=CompletedSessionResponse)
def create_completed_session(
    session: CompletedSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Parse the ISO8601 date string to datetime
        session_date = datetime.fromisoformat(session.date.replace('Z', '+00:00'))

        # Check for duplicate sessions (same user, same date, same drill count)
        existing_session = db.query(CompletedSession).filter(
            CompletedSession.user_id == current_user.id,
            CompletedSession.date == session_date,
            CompletedSession.total_drills == session.total_drills,
            CompletedSession.total_completed_drills == session.total_completed_drills,
            CompletedSession.session_type == session.session_type
        ).first()
        
        is_new_session = existing_session is None
        
        if existing_session:
            # Return existing session instead of creating duplicate
            # Don't grant treats again (idempotency)
            treats_awarded = 0
            treats_already_granted = True
            db_session = existing_session
        else:
            # Create the completed session
            db_session = CompletedSession(
                user_id=current_user.id,
                date=session_date,
                total_completed_drills=session.total_completed_drills,
                total_drills=session.total_drills,
                session_type=session.session_type,
                drills=[{
                    "drill": {
                        "uuid": drill.drill.uuid,
                        "title": drill.drill.title,
                        "skill": drill.drill.skill,
                        "subSkills": drill.drill.subSkills,
                        "sets": drill.drill.sets,
                        "reps": drill.drill.reps,
                        "duration": drill.drill.duration,
                        "description": drill.drill.description,
                        "instructions": drill.drill.instructions,
                        "tips": drill.drill.tips,
                        "equipment": drill.drill.equipment,
                        "trainingStyle": drill.drill.trainingStyle,
                        "difficulty": drill.drill.difficulty,
                        "videoUrl": drill.drill.videoUrl
                    },
                    "setsDone": drill.setsDone,
                    "totalSets": drill.totalSets,
                    "totalReps": drill.totalReps,
                    "totalDuration": drill.totalDuration,
                    "isCompleted": drill.isCompleted
                } for drill in session.drills] if session.drills else None,
                duration_minutes=session.duration_minutes
            )
            db.add(db_session)
            db.commit()
            db.refresh(db_session)
        
        # ✅ Update streak in progress history (existing code - keep separate!)
        progress_history = db.query(ProgressHistory).filter(
            ProgressHistory.user_id == current_user.id
        ).first()
        
        session_date_only = session_date.date()
        
        # Get the previous session (before this one)
        previous_session = db.query(CompletedSession).filter(
            CompletedSession.user_id == current_user.id,
            CompletedSession.id != db_session.id
        ).order_by(CompletedSession.date.desc()).first()
        
        if progress_history:
            # Update streak using helper function
            update_streak_on_session_completion(
                progress_history=progress_history,
                session_date=session_date_only,
                previous_session=previous_session
            )
            db.commit()
        
        # ✅ NEW: Calculate and grant treats (only for new sessions)
        treats_awarded = 0
        treats_already_granted = False
        
        if is_new_session:
            treat_service = TreatRewardService(db)
            
            # Prepare session data for calculation
            session_data = {
                'session_type': session.session_type or 'drill_training',
                'drills': session.drills or [],
                'total_completed_drills': session.total_completed_drills or 0,
                'total_drills': session.total_drills or 0,
                'duration_minutes': session.duration_minutes,
            }
            
            # Get user context (streak from progress_history, refreshed after update)
            if progress_history:
                db.refresh(progress_history)  # Refresh to get updated streak
            
            user_context = {
                'current_streak': progress_history.current_streak if progress_history else 0,
                'previous_streak': progress_history.previous_streak if progress_history else 0,
            }
            
            # Grant treats (only for new sessions)
            treats_awarded, treats_already_granted = treat_service.grant_session_reward(
                user=current_user,
                session_data=session_data,
                is_new_session=is_new_session,
                user_context=user_context
            )
        
        # Prepare response with treats information
        response_data = {
            **db_session.dict(),  # Existing session data
            'treats_awarded': treats_awarded,
            'treats_already_granted': treats_already_granted,
        }
        
        return response_data
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create completed session: {str(e)}"
        )

# response schema
# app/schemas/sessions.py

class CompletedSessionResponse(CompletedSessionBase):
    """Response schema including treat reward information"""
    id: int
    user_id: int
    treats_awarded: int  # ✅ NEW: Treats granted for this session
    treats_already_granted: bool  # ✅ NEW: Whether treats were already granted (idempotency)
    
    model_config = ConfigDict(from_attributes=True)

# what our current frontend sends right now: