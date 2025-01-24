"""
drills.py
API endpoints for obtaining drills and recommendations
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from db import get_db
from models import Drill, DrillCategory
from typing import List, Optional

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
            func.cast(Drill.required_equipment, JSONB).contained_by(
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
                "id": drill.id,
                "title": drill.title,
                "description": drill.description,
                "category": drill.category.name,
                "duration": drill.duration,
                "difficulty": drill.difficulty,
                "equipment": drill.required_equipment,
                "instructions": drill.instructions,
                "tips": drill.tips
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
