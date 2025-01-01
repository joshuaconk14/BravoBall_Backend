"""
drills.py
API endpoints for obtaining drills and recommendations
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from models import Drill, DrillCategory, User
from auth import get_current_user
from routers.services.drill_recommender import DrillRecommender
from typing import List

router = APIRouter()

# API endpoint for obtaining all drills for the Drill Catalog page of the app
@router.get("/drills/")
def get_drills(
    category: str = None, 
    difficulty: str = None,
    equipment: List[str] = None,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    # Start with base query
    query = db.query(Drill)
    
    # Apply filters if provided
    if category:
        query = query.join(DrillCategory).filter(DrillCategory.name == category)
    if difficulty:
        query = query.filter(Drill.difficulty == difficulty)
    if equipment:
        # Filter drills that require only available equipment
        query = query.filter(Drill.recommended_equipment.contained_by(equipment))
    
    # Calculate pagination
    total = query.count()
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
                "equipment": drill.recommended_equipment,
                "instructions": drill.instructions,
                "tips": drill.tips,
                "video_url": drill.video_url
            } for drill in drills
        ],
        "metadata": {
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1
        },
        "filters": {
            "categories": [cat.name for cat in db.query(DrillCategory).all()],
            "difficulties": ["Beginner", "Intermediate", "Competitive", "Professional"],
            "equipment": list(set([item for drill in db.query(Drill.recommended_equipment).all() for item in drill[0]]))
        }
    }

# API endpoint for obtaining all drill categories
@router.get("/drill-categories/")
def get_categories(db: Session = Depends(get_db)):
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

# API endpoint for obtaining recommendations
@router.get("/drills/recommendations/")
def get_recommendations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recommender = DrillRecommender(db)
    recommended_drills = recommender.get_recommendations(user)

    # Return drills in JSON format with metadata for frontend to display with pagination and filters
    return {
        "status": "success",
        "recommendations": [
            {
                "id": drill.id,
                "title": drill.title,
                "description": drill.description,
                "category": drill.category.name,
                "duration": drill.duration,
                "difficulty": drill.difficulty,
                "recommended_equipment": drill.recommended_equipment,
                "instructions": drill.instructions,
                "tips": drill.tips,
                "video_url": drill.video_url,
                "matchScore": {
                    "skillLevelMatch": True if drill.difficulty == user.skill_level else False,
                    "equipmentAvailable": all(item in user.available_equipment for item in drill.recommended_equipment),
                    "recommendedForPosition": user.position in drill.recommended_positions if drill.recommended_positions else False,
                    "calculatedScore": round(score, 2)
                }
            } for drill, score in recommended_drills
        ],
        "metadata": {
            "totalDrills": len(recommended_drills),
            "userSkillLevel": user.skill_level,
            "userPosition": user.position,
            "availableEquipment": user.available_equipment
        }
    }