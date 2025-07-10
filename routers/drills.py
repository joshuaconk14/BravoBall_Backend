"""
drills.py
API endpoints for obtaining drills and recommendations
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from db import get_db
from models import Drill, DrillCategory, DrillResponse, User
from typing import List, Optional
from sqlalchemy import or_
import logging
from auth import get_current_user
from routers.router_utils import drill_to_response


router = APIRouter()

@router.get("/drills/")
def get_drills(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    equipment: Optional[List[str]] = None,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get drills with optional filtering and pagination"""
    query = db.query(Drill)

    # Apply filters if provided
    if category:
        query = query.join(DrillCategory).filter(DrillCategory.name == category)
    
    if difficulty:
        query = query.filter(Drill.difficulty == difficulty)
    
    if equipment:
        # Use PostgreSQL JSONB containment operator
        query = query.filter(
            func.cast(Drill.equipment, JSONB).contained_by(
                func.cast(equipment, JSONB)
            )
        )

    # Get total count before pagination
    total = query.count()
    
    # Apply pagination
    drills = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "drills": [
            {
                "uuid": str(drill.uuid),  # Use UUID instead of id
                "title": drill.title,
                "description": drill.description,
                "category": drill.category.name if drill.category else "",
                "duration": drill.duration if drill.duration is not None else 10,  # Default to 10 minutes
                "difficulty": drill.difficulty if drill.difficulty else "beginner",
                "equipment": drill.equipment if drill.equipment else [],
                "instructions": drill.instructions if drill.instructions else [],
                "tips": drill.tips if drill.tips else []
            } for drill in drills
        ],
        "metadata": {
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1
        }
    }

# API endpoint for obtaining all drill categories
@router.get("/drill-categories/")
def get_categories(db: Session = Depends(get_db)):
    """Get all drill categories"""
    categories = db.query(DrillCategory).all()
    return {
        "categories": [
            {
                "id": category.id,
                "name": category.name,
                "description": category.description
            } for category in categories
        ]
    }


# Add a search endpoint to find drills
@router.get("/api/drills/search")
async def search_drills(
    query: str = "",
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search for drills based on various criteria.
    Used when users want to find drills to add to their groups.
    """
    try:
        # Start with a base query
        drill_query = db.query(Drill)
        
        # Apply text search if provided
        if query:
            # Search in title and description
            drill_query = drill_query.filter(
                or_(
                    Drill.title.ilike(f"%{query}%"),
                    Drill.description.ilike(f"%{query}%")
                )
            )
        
        # Apply category filter if provided
        if category:
            drill_query = drill_query.join(DrillCategory).filter(
                DrillCategory.name.ilike(f"%{category}%")
            )
        
        # Apply difficulty filter if provided
        if difficulty:
            drill_query = drill_query.filter(
                Drill.difficulty == difficulty
            )
        
        # Get total count for pagination
        total = drill_query.count()
        
        # Apply pagination
        drills = drill_query.offset((page - 1) * limit).limit(limit).all()
        
        # Convert to response format
        drill_responses = []
        for drill in drills:
            drill_responses.append(drill_to_response(drill, db))
        
        # Include pagination metadata
        response = {
            "items": drill_responses,
            "total": total,
            "page": page,
            "page_size": limit,
            "total_pages": (total + limit - 1) // limit
        }
        
        return response
    except Exception as e:
        logging.error(f"Error searching drills: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search drills: {str(e)}") 



# For testing: public search endpoint that doesn't require authentication
@router.get("/public/drills/search")
async def public_search_drills(
    query: str = "",
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    A public search endpoint for drills that doesn't require authentication.
    Useful for testing and public access to drill information.
    """
    try:
        # Start with a base query
        drill_query = db.query(Drill)
        
        # Apply text search if provided
        if query:
            # Search in title and description
            drill_query = drill_query.filter(
                or_(
                    Drill.title.ilike(f"%{query}%"),
                    Drill.description.ilike(f"%{query}%")
                )
            )
        
        # Apply category filter if provided
        if category:
            drill_query = drill_query.join(DrillCategory).filter(
                DrillCategory.name.ilike(f"%{category}%")
            )
        
        # Apply difficulty filter if provided
        if difficulty:
            drill_query = drill_query.filter(
                Drill.difficulty == difficulty
            )
        
        # Get total count for pagination
        total = drill_query.count()
        
        # Apply pagination
        drills = drill_query.offset((page - 1) * limit).limit(limit).all()
        
        # Convert to response format
        drill_responses = []
        for drill in drills:
            drill_responses.append(drill_to_response(drill, db))
        
        # Include pagination metadata
        response = {
            "items": drill_responses,
            "total": total,
            "page": page,
            "page_size": limit,
            "total_pages": (total + limit - 1) // limit
        }
        
        return response
    except Exception as e:
        logging.error(f"Error searching drills: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search drills: {str(e)}") 