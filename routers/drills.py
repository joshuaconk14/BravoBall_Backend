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

router = APIRouter()

# API endpoint for obtaining all drills
@router.get("/drills/")
def get_drills(category: str = None, db: Session = Depends(get_db)):
    query = db.query(Drill)
    if category:
        query = query.join(DrillCategory).filter(DrillCategory.name == category)
    
    drills = query.all()
    return {
        "drills": [
            {
                "id": drill.id,
                "title": drill.title,
                "description": drill.description,
                "category": drill.category.name,
                "duration": drill.duration,
                "difficulty": drill.difficulty,
                "equipment": drill.equipment,
                "instructions": drill.instructions,
                "tips": drill.tips,
                "video_url": drill.video_url
            } for drill in drills
        ]
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

    return {
        "recommendations": [
            {
                "id": drill.id,
                "title": drill.title,
                "description": drill.description,
                "category": drill.category.name,
                "duration": drill.duration,
                "difficulty": drill.difficulty,
                "equipment": drill.equipment,
                "instructions": drill.instructions,
                "tips": drill.tips,
                "video_url": drill.video_url,
                "skill_focus": drill.skill_focus
            } for drill in recommended_drills
        ]
    }