from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime
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
                result.append({
                    "drill": {
                        "backend_id": drill.id,
                        "title": drill.title,
                        "skill": getattr(drill, 'skill', None),
                        "sets": drill.sets,
                        "reps": drill.reps,
                        "duration": drill.duration,
                        "description": drill.description,
                        "tips": drill.tips,
                        "equipment": drill.equipment,
                        "trainingStyle": getattr(drill, 'trainingStyle', None),
                        "difficulty": drill.difficulty
                    },
                    # Add per-session fields as needed
                    "sets": ordered_drill.sets,
                    "reps": ordered_drill.reps,
                    "duration": ordered_drill.duration,
                    "is_completed": ordered_drill.is_completed,
                    "position": ordered_drill.position
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
        # Get all sessions for this user
        user_sessions = db.query(TrainingSession).filter(TrainingSession.user_id == current_user.id).all()
        session_ids = [s.id for s in user_sessions]
        # Get existing ordered drills for this user's sessions
        existing_drills = {
            (drill.session_id, drill.drill_id): drill
            for drill in db.query(OrderedSessionDrill).filter(
                OrderedSessionDrill.session_id.in_(session_ids)
            ).all()
        }
        processed_keys = set()
        # Add or update ordered drills
        for position, drill_data in enumerate(ordered_drills.ordered_drills):
            drill = db.query(Drill).filter(Drill.id == drill_data.drill.backend_id).first()
            if not drill and drill_data.drill.backend_id:
                raise HTTPException(status_code=404, detail=f"Drill with id {drill_data.drill.backend_id} not found")
            drill_id = drill.id if drill else None
            session_id = drill_data.session_id  # Must be provided by frontend
            key = (session_id, drill_id)
            processed_keys.add(key)
            if key in existing_drills:
                # Update existing drill
                existing_drill = existing_drills[key]
                existing_drill.position = position
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
                    sets=drill_data.sets,
                    reps=drill_data.reps,
                    duration=drill_data.duration,
                    is_completed=drill_data.is_completed
                )
                db.add(ordered_drill)
        # Delete drills that were removed
        for key, drill in existing_drills.items():
            if key not in processed_keys:
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
        
        # Create the completed session
        db_session = CompletedSession(
            user_id=current_user.id,
            date=session_date,
            total_completed_drills=session.total_completed_drills,
            total_drills=session.total_drills,
            drills=[{
                "drill": {
                    "id": drill.drill.id,
                    "title": drill.drill.title,
                    "skill": drill.drill.skill,
                    "sets": drill.drill.sets,
                    "reps": drill.drill.reps,
                    "duration": drill.drill.duration,
                    "description": drill.drill.description,
                    "tips": drill.drill.tips,
                    "equipment": drill.drill.equipment,
                    "trainingStyle": drill.drill.trainingStyle,
                    "difficulty": drill.drill.difficulty
                },
                "setsDone": drill.setsDone,
                "totalSets": drill.totalSets,
                "totalReps": drill.totalReps,
                "totalDuration": drill.totalDuration,
                "isCompleted": drill.isCompleted
            } for drill in session.drills]
        )
        db.add(db_session)
        
        # # Update progress history
        # progress_history = db.query(ProgressHistory).filter(
        #     ProgressHistory.user_id == current_user.id
        # ).first()
        
        # if progress_history:
        #     progress_history.completed_sessions_count += 1
        #     # TODO: Implement proper streak calculation based on consecutive days
        # else:
        #     progress_history = ProgressHistory(
        #         user_id=current_user.id,
        #         completed_sessions_count=1
        #     )
        #     db.add(progress_history)
        
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


# Drill Groups Endpoints
@router.post("/api/drills/groups/", response_model=DrillGroupSchema)
def create_drill_group(group: DrillGroupCreate,
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    db_group = DrillGroup(**group.dict(), user_id=current_user.id)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group

@router.get("/api/drills/groups/", response_model=List[DrillGroupSchema])
def get_drill_groups(current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    return db.query(DrillGroup).filter(DrillGroup.user_id == current_user.id).all()

@router.put("/api/drills/groups/{group_id}", response_model=DrillGroupSchema)
def update_drill_group(group_id: int,
                      group: DrillGroupUpdate,
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    db_group = db.query(DrillGroup).filter(
        DrillGroup.id == group_id,
        DrillGroup.user_id == current_user.id
    ).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Drill group not found")
    
    for field, value in group.dict(exclude_unset=True).items():
        setattr(db_group, field, value)
    
    db.commit()
    db.refresh(db_group)
    return db_group

@router.delete("/api/drills/groups/{group_id}")
def delete_drill_group(group_id: int,
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    db_group = db.query(DrillGroup).filter(
        DrillGroup.id == group_id,
        DrillGroup.user_id == current_user.id
    ).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Drill group not found")
    
    db.delete(db_group)
    db.commit()
    return {"message": "Drill group deleted"}

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

        if not progress_history:
            # If no progress history exists, return default values
            progress_history = ProgressHistory(
                user_id=current_user.id,
                current_streak=0,
                highest_streak=0,
                completed_sessions_count=0
            )
            db.add(progress_history)
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
                highest_streak=progress.highest_streak,
                completed_sessions_count=progress.completed_sessions_count
            )
            db.add(progress_history)
        else:
            # Update existing progress history
            progress_history.current_streak = progress.current_streak
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