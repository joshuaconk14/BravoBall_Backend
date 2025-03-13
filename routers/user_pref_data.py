from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from models import User, UserPreferences, CompletedSession, DrillGroup
from schemas import (
    UserPreferences as UserPreferencesSchema,
    UserPreferencesUpdate,
    CompletedSession as CompletedSessionSchema,
    CompletedSessionCreate,
    DrillGroup as DrillGroupSchema,
    DrillGroupCreate,
    DrillGroupUpdate
)
from db import get_db
from auth import get_current_user

router = APIRouter()

# User Preferences Endpoints
@router.get("/api/preferences/", response_model=UserPreferencesSchema)
def get_user_preferences(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    preferences = db.query(UserPreferences).filter(UserPreferences.user_id == current_user.id).first()
    if not preferences:
        # Create default preferences if none exist
        preferences = UserPreferences(user_id=current_user.id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    return preferences

@router.put("/api/preferences/", response_model=UserPreferencesSchema)
def update_user_preferences(preferences: UserPreferencesUpdate, 
                          current_user: User = Depends(get_current_user), 
                          db: Session = Depends(get_db)):
    db_preferences = db.query(UserPreferences).filter(UserPreferences.user_id == current_user.id).first()
    if not db_preferences:
        db_preferences = UserPreferences(user_id=current_user.id)
        db.add(db_preferences)
    
    for field, value in preferences.dict(exclude_unset=True).items():
        setattr(db_preferences, field, value)
    
    db.commit()
    db.refresh(db_preferences)
    return db_preferences

# Completed Sessions Endpoints
@router.post("/api/sessions/completed/", response_model=CompletedSessionSchema)
def create_completed_session(session: CompletedSessionCreate,
                           current_user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    db_session = CompletedSession(**session.dict(), user_id=current_user.id)
    db.add(db_session)
    
    # Update user stats
    preferences = db.query(UserPreferences).filter(UserPreferences.user_id == current_user.id).first()
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