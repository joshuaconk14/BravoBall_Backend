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

# ordered drills endpoint
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
        # Get existing ordered drills for this user by filtering for id
        existing_drills = {
            drill.drill_id: drill 
            for drill in db.query(OrderedSessionDrill).filter(
                OrderedSessionDrill.user_id == current_user.id
            ).all()
        }
        
        # Track which drills we've processed to identify deleted ones
        processed_drill_ids = set()
        
        # Add or update ordered drills
        for position, drill_data in enumerate(ordered_drills.ordered_drills):
            # Get or verify the drill exists
            drill = db.query(Drill).filter(Drill.id == drill_data.drill.backend_id).first()
            if not drill and drill_data.drill.backend_id:
                raise HTTPException(status_code=404, detail=f"Drill with id {drill_data.drill.backend_id} not found")
            
            drill_id = drill.id if drill else None
            # adding non-deleted drill id's to processed_drill_id set
            processed_drill_ids.add(drill_id)
            
            if drill_id in existing_drills:
                # Update existing drill
                existing_drill = existing_drills[drill_id]
                existing_drill.position = position
                existing_drill.sets_done = drill_data.sets_done
                existing_drill.total_sets = drill_data.total_sets
                existing_drill.total_reps = drill_data.total_reps
                existing_drill.total_duration = drill_data.total_duration
                existing_drill.is_completed = drill_data.is_completed
            else:
                # Add new drill
                ordered_drill = OrderedSessionDrill(
                    user_id=current_user.id,
                    drill_id=drill_id,
                    position=position,
                    sets_done=drill_data.sets_done,
                    total_sets=drill_data.total_sets,
                    total_reps=drill_data.total_reps,
                    total_duration=drill_data.total_duration,
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