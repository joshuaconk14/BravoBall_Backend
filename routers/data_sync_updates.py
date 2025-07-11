from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime, timedelta
from models import User, CompletedSession, DrillGroup, OrderedSessionDrill, Drill, ProgressHistory, TrainingSession
from schemas import (
    CompletedSession as CompletedSessionSchema,
    CompletedSessionCreate,
    DrillGroup as DrillGroupSchema,
    DrillGroupCreate,
    DrillGroupUpdate,
    OrderedSessionDrillUpdate,
    ProgressHistoryUpdate,
    ProgressHistoryResponse
)
from db import get_db
from auth import get_current_user

router = APIRouter()

# ordered drills endpoint
@router.get("/api/sessions/ordered_drills/")
async def get_ordered_session_drills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the user's current ordered drills and their progress.
    """
    try:
        # Join OrderedSessionDrill with TrainingSession to filter by user
        ordered_drills = db.query(OrderedSessionDrill).join(OrderedSessionDrill.session).filter(
            TrainingSession.user_id == current_user.id
        ).options(joinedload(OrderedSessionDrill.drill)).order_by(OrderedSessionDrill.position).all()

        # Include the associated drill data for each ordered drill
        result = []
        for ordered_drill in ordered_drills:
            drill = ordered_drill.drill
            if drill:
                # Get skill focus data
                skill_focus = drill.skill_focus
                primary_skill = next((sf for sf in skill_focus if sf.is_primary), None) if skill_focus else None
                secondary_skills = [sf for sf in skill_focus if not sf.is_primary] if skill_focus else []
                
                # Collect all sub-skills (primary + secondary)
                sub_skills = []
                if primary_skill:
                    sub_skills.append(primary_skill.sub_skill)
                sub_skills.extend([skill.sub_skill for skill in secondary_skills])
                
                # Get the main skill category (from primary skill)
                main_skill = primary_skill.category if primary_skill else "general"
                
                result.append({
                    "drill": {
                        "uuid": str(drill.uuid),  # Keep UUID field, remove backend_id
                        "title": drill.title,
                        "skill": main_skill,
                        "subSkills": sub_skills,
                        "sets": drill.sets,
                        "reps": drill.reps,
                        "duration": drill.duration,
                        "description": drill.description,
                        "instructions": drill.instructions,
                        "tips": drill.tips,
                        "equipment": drill.equipment,
                        "trainingStyle": drill.training_styles[0],
                        "difficulty": drill.difficulty,
                        "videoUrl": drill.video_url
                    },
                    # Add per-session fields as needed
                    "sets_done": ordered_drill.sets_done,
                    "sets": ordered_drill.sets,
                    "reps": ordered_drill.reps,
                    "duration": ordered_drill.duration,
                    "is_completed": ordered_drill.is_completed,
                    "position": ordered_drill.position # position in db
                })

        return {
            "ordered_drills": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get ordered session drills: {str(e)}"
        )

@router.put("/api/sessions/ordered_drills/")
async def sync_ordered_session_drills(
    ordered_drills: OrderedSessionDrillUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync the user's current drill progress. This only maintains the current state,
    not historical data. Historical data is saved to completed_sessions when a session
    is marked as complete.
    """
    try:
        # Get or create the user's training session
        user_session = db.query(TrainingSession).filter(TrainingSession.user_id == current_user.id).first()
        if not user_session:
            # Create a new training session for the user
            user_session = TrainingSession(
                user_id=current_user.id,
                total_duration=0,  # Will be calculated based on drills
                focus_areas=[]
            )
            db.add(user_session)
            db.commit()
            db.refresh(user_session)
        
        session_id = user_session.id
        
        # Get existing ordered drills for this user's session
        existing_drills = {
            drill.drill_id: drill
            for drill in db.query(OrderedSessionDrill).filter(
                OrderedSessionDrill.session_id == session_id
            ).all()
        }
        processed_drill_ids = set()
        
        # Add or update ordered drills
        for position, drill_data in enumerate(ordered_drills.ordered_drills):
            # Find drill by UUID
            drill = None
            if drill_data.drill.uuid:
                drill = db.query(Drill).filter(Drill.uuid == drill_data.drill.uuid).first()
            
            if not drill:
                raise HTTPException(status_code=404, detail=f"Drill not found with uuid {drill_data.drill.uuid}")
            
            drill_id = drill.id if drill else None
            processed_drill_ids.add(drill_id)
            
            if drill_id in existing_drills:
                # Update existing drill
                existing_drill = existing_drills[drill_id]
                existing_drill.position = position
                existing_drill.sets_done = drill_data.sets_done
                existing_drill.sets = drill_data.sets
                existing_drill.reps = drill_data.reps
                existing_drill.duration = drill_data.duration
                existing_drill.is_completed = drill_data.is_completed
            else:
                # Add new drill
                ordered_drill = OrderedSessionDrill(
                    session_id=session_id,
                    drill_id=drill_id,
                    position=position,
                    sets_done = drill_data.sets_done,
                    sets=drill_data.sets,
                    reps=drill_data.reps,
                    duration=drill_data.duration,
                    is_completed=drill_data.is_completed
                )
                db.add(ordered_drill)
        
        # Delete drills that were removed
        for drill_id, drill in existing_drills.items():
            if drill_id not in processed_drill_ids:
                db.delete(drill)
        
        db.commit()
        return {
            "message": "Current drill progress synced successfully",
            "total_drills": len(ordered_drills.ordered_drills),
            "completed_drills": sum(1 for drill in ordered_drills.ordered_drills if drill.is_completed)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync ordered session drills: {str(e)}"
        )
    

# Completed Sessions Endpoints
@router.post("/api/sessions/completed/", response_model=CompletedSessionSchema)
def create_completed_session(session: CompletedSessionCreate,
                           current_user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    try:
        # Parse the ISO8601 date string to datetime
        session_date = datetime.fromisoformat(session.date.replace('Z', '+00:00'))

        # Check for duplicate sessions (same user, same date, same drill count)
        existing_session = db.query(CompletedSession).filter(
            CompletedSession.user_id == current_user.id,
            CompletedSession.date == session_date,
            CompletedSession.total_drills == session.total_drills,
            CompletedSession.total_completed_drills == session.total_completed_drills
        ).first()
        
        if existing_session:
            # Return existing session instead of creating duplicate
            return existing_session
        
        # Create the completed session
        db_session = CompletedSession(
            user_id=current_user.id,
            date=session_date,
            total_completed_drills=session.total_completed_drills,
            total_drills=session.total_drills,
            drills=[{
                "drill": {
                    "uuid": drill.drill.uuid,  # Use UUID as primary identifier
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
            } for drill in session.drills]
        )
        db.add(db_session)
        
        db.commit()
        db.refresh(db_session)
        return db_session
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create completed session: {str(e)}"
        )

@router.get("/api/sessions/completed/", response_model=List[CompletedSessionSchema])
def get_completed_sessions(current_user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    return db.query(CompletedSession).filter(CompletedSession.user_id == current_user.id).all()




# Progress History Endpoints
@router.get("/api/progress_history/", response_model=ProgressHistoryResponse)
async def get_progress_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the user's progress history (streaks and completed sessions count)
    """
    try:
        progress_history = db.query(ProgressHistory).filter(
            ProgressHistory.user_id == current_user.id
        ).first()

        # Fetch all completed sessions for the user, ordered by date ascending
        completed_sessions = db.query(CompletedSession).filter(
            CompletedSession.user_id == current_user.id
        ).order_by(CompletedSession.date.asc()).all()
        completed_sessions_count = len(completed_sessions)

        # Calculate streaks
        streak = 0
        highest_streak = 0
        previous_streak = progress_history.current_streak if progress_history else 0
        today = datetime.now().date()
        last_session_date = None

        for session in completed_sessions:
            session_date = session.date.date() if hasattr(session.date, 'date') else session.date
            if last_session_date is None:
                streak = 1
            else:
                days_diff = (session_date - last_session_date).days
                if days_diff == 1:
                    streak += 1
                elif days_diff == 0:
                    # Same day, don't increment streak
                    pass
                else:
                    streak = 1
            highest_streak = max(highest_streak, streak)
            last_session_date = session_date

        # Check if the last session was today, yesterday, or 2 days ago
        streak_should_reset = True
        if last_session_date:
            if (today - last_session_date).days in [0, 1, 2]:
                streak_should_reset = False

        if streak_should_reset:
            previous_streak = streak
            streak = 0

        if not progress_history:
            # Create default progress history if none exists
            progress_history = ProgressHistory(
                user_id=current_user.id,
                current_streak=streak,
                previous_streak=previous_streak,
                highest_streak=highest_streak,
                completed_sessions_count=completed_sessions_count
            )
            db.add(progress_history)
            db.commit()
            db.refresh(progress_history)
        else:
            progress_history.previous_streak = previous_streak
            progress_history.current_streak = streak
            progress_history.highest_streak = highest_streak
            progress_history.completed_sessions_count = completed_sessions_count
            db.commit()
            db.refresh(progress_history)

        return progress_history

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get progress history: {str(e)}"
        )

@router.put("/api/progress_history/", response_model=ProgressHistoryResponse)
async def sync_progress_history(
    progress: ProgressHistoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync the user's progress history (streaks and completed sessions count)
    """
    try:
        # Get or create progress history for the user
        progress_history = db.query(ProgressHistory).filter(
            ProgressHistory.user_id == current_user.id
        ).first()

        if not progress_history:
            progress_history = ProgressHistory(
                user_id=current_user.id,
                current_streak=progress.current_streak,
                previous_streak=progress.previous_streak, # Add previous_streak field
                highest_streak=progress.highest_streak,
                completed_sessions_count=progress.completed_sessions_count
            )
            db.add(progress_history)
        else:
            # Update existing progress history
            progress_history.current_streak = progress.current_streak
            progress_history.previous_streak = progress.previous_streak # Add previous_streak field
            progress_history.highest_streak = progress.highest_streak
            progress_history.completed_sessions_count = progress.completed_sessions_count

        db.commit()
        db.refresh(progress_history)
        
        return progress_history
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync progress history: {str(e)}"
        )