from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import User, SavedFilter, SavedFilterCreate, SavedFilterUpdate, SavedFilterResponse
from db import get_db
from auth import get_current_user

router = APIRouter()

# Create new filters
@router.post("/api/filters/", response_model=List[SavedFilterResponse])
async def create_saved_filter(
    filters: SavedFilterCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new saved filters for the current user"""
    try:
        created_filters = []
        for filter_data in filters.saved_filters:
            # Create new filter
            db_filter = SavedFilter(
                client_id=filter_data.id,
                user_id=current_user.id,
                name=filter_data.name,
                saved_time=filter_data.saved_time,
                saved_equipment=filter_data.saved_equipment,
                saved_training_style=filter_data.saved_training_style,
                saved_location=filter_data.saved_location,
                saved_difficulty=filter_data.saved_difficulty
            )
            db.add(db_filter)
            created_filters.append(db_filter)
        
        db.commit()
        return [format_filter_response(filter) for filter in created_filters]
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create saved filters: {str(e)}")

# Update existing filters
@router.put("/api/filters/{filter_id}", response_model=SavedFilterResponse)
async def update_saved_filter(
    filter_id: str,  # Using string for client_id
    filter: SavedFilterUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing saved filter"""
    try:
        # Find filter by client_id
        existing_filter = db.query(SavedFilter).filter(
            SavedFilter.client_id == filter_id,
            SavedFilter.user_id == current_user.id
        ).first()
        
        if not existing_filter:
            raise HTTPException(status_code=404, detail="Saved filter not found")
        
        # Update fields
        for field, value in filter.dict(exclude_unset=True).items():
            if value is not None:
                setattr(existing_filter, field, value)
        
        db.commit()
        db.refresh(existing_filter)
        return format_filter_response(existing_filter)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update filter: {str(e)}")

# Helper function for consistent response formatting
def format_filter_response(filter: SavedFilter) -> dict:
    return {
        "id": filter.client_id,  # Client UUID
        "backend_id": filter.id,  # Backend ID
        "name": filter.name,
        "saved_time": filter.saved_time,
        "saved_equipment": filter.saved_equipment,
        "saved_training_style": filter.saved_training_style,
        "saved_location": filter.saved_location,
        "saved_difficulty": filter.saved_difficulty
    }

@router.get("/api/filters/", response_model=List[SavedFilterResponse])
async def get_saved_filters(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all saved filters for the current user"""
    return db.query(SavedFilter).filter(SavedFilter.user_id == current_user.id).all()

@router.delete("/api/filters/{filter_id}")
async def delete_saved_filter(
    filter_id: int,  # Changed back to int
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