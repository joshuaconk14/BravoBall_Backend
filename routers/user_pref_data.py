from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from models import User, CompletedSession, DrillGroup, OrderedSessionDrill, Drill, ProgressHistory
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

#ordered Session drills
@router.put("/api/sessions/ordered_drills/")
async def sync_ordered_session_drills(
    ordered_drills: OrderedSessionDrillUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync the ordered drills for a session with their completion status and progress.
    """
    try:
        # Get or create a session for the user
        session = db.query(CompletedSession).filter(
            CompletedSession.user_id == current_user.id,
            CompletedSession.date == datetime.now().date()
        ).first()

        if not session:
            session = CompletedSession(
                user_id=current_user.id,
                date=datetime.now(),
                total_completed_drills=0,
                total_drills=len(ordered_drills.ordered_drills),
                drills=[]
            )
            db.add(session)
            db.commit()
            db.refresh(session)

        # Delete existing ordered drills for this session
        db.query(OrderedSessionDrill).filter(
            OrderedSessionDrill.session_id == session.id
        ).delete()
        
        # Add new ordered drills
        for position, drill_data in enumerate(ordered_drills.ordered_drills):
            # Get or create the drill in the database
            drill = db.query(Drill).filter(Drill.id == drill_data.drill.backend_id).first()
            if not drill and drill_data.drill.backend_id:
                # If we have a backend_id but no drill, something's wrong
                raise HTTPException(status_code=404, detail=f"Drill with id {drill_data.drill.backend_id} not found")
            
            # Create the ordered drill
            ordered_drill = OrderedSessionDrill(
                session_id=session.id,
                drill_id=drill.id if drill else None,
                position=position,
                sets_done=drill_data.sets_done,
                total_sets=drill_data.total_sets,
                total_reps=drill_data.total_reps,
                total_duration=drill_data.total_duration,
                is_completed=drill_data.is_completed
            )
            db.add(ordered_drill)

        # Update completion counts
        completed_count = sum(1 for drill in ordered_drills.ordered_drills if drill.is_completed)
        session.total_completed_drills = completed_count
        session.total_drills = len(ordered_drills.ordered_drills)
        
        db.commit()
        
        return {
            "message": "Session drills synced successfully",
            "total_drills": len(ordered_drills.ordered_drills),
            "completed_drills": completed_count
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
    db_session = CompletedSession(**session.dict(), user_id=current_user.id)
    db.add(db_session)
    
    # Update user stats
    preferences = db.query(CompletedSession).filter(CompletedSession.user_id == current_user.id).first()
    if preferences:
        preferences.completed_sessions_count += 1
        # Update streak logic here
        # TODO: Implement proper streak calculation based on consecutive days
    
    db.commit()
    db.refresh(db_session)
    return db_session

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