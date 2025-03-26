from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import User, SavedFilter, SavedFilterCreate, SavedFilterUpdate, SavedFilterResponse
from db import get_db
from auth import get_current_user

router = APIRouter()

@router.post("/api/filters/", response_model=SavedFilterResponse)
async def create_saved_filter(
    filter: SavedFilterCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new saved filter for the current user"""
    # Check if filter with this ID already exists
    existing_filter = db.query(SavedFilter).filter(SavedFilter.id == filter.id).first()
    if existing_filter:
        raise HTTPException(status_code=400, detail="Filter with this ID already exists")

    db_filter = SavedFilter(**filter.dict(), user_id=current_user.id)
    db.add(db_filter)
    db.commit()
    db.refresh(db_filter)
    return db_filter

@router.get("/api/filters/", response_model=List[SavedFilterResponse])
async def get_saved_filters(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all saved filters for the current user"""
    return db.query(SavedFilter).filter(SavedFilter.user_id == current_user.id).all()

@router.put("/api/filters/{filter_id}", response_model=SavedFilterResponse)
async def update_saved_filter(
    filter_id: str,  # Changed from int to str
    filter: SavedFilterUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a saved filter"""
    db_filter = db.query(SavedFilter).filter(
        SavedFilter.id == filter_id,
        SavedFilter.user_id == current_user.id
    ).first()
    
    if not db_filter:
        raise HTTPException(status_code=404, detail="Saved filter not found")
    
    for field, value in filter.dict(exclude_unset=True).items():
        if value is not None:  # Only update non-None values
            setattr(db_filter, field, value)
    
    db.commit()
    db.refresh(db_filter)
    return db_filter

@router.delete("/api/filters/{filter_id}")
async def delete_saved_filter(
    filter_id: str,  # Changed from int to str
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a saved filter"""
    db_filter = db.query(SavedFilter).filter(
        SavedFilter.id == filter_id,
        SavedFilter.user_id == current_user.id
    ).first()
    
    if not db_filter:
        raise HTTPException(status_code=404, detail="Saved filter not found")
    
    db.delete(db_filter)
    db.commit()
    return {"message": "Filter deleted successfully"} 