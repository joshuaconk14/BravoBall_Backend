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
        # ✅ UPDATED: Map frontend category name to backend database name
        backend_category = map_frontend_category_to_backend(category)
        query = query.join(DrillCategory).filter(DrillCategory.name == backend_category)
    
    if difficulty:
        query = query.filter(func.lower(Drill.difficulty) == difficulty.lower())
    
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
                func.lower(Drill.difficulty) == difficulty.lower()
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


# ✅ NEW: Helper function to map frontend category names to backend database category names
def map_frontend_category_to_backend(frontend_category: str) -> str:
    """
    Map frontend category names (with spaces) to backend database category names (with underscores)
    """
    category_mapping = {
        "Passing": "passing",
        "Shooting": "shooting", 
        "Dribbling": "dribbling",
        "First Touch": "first_touch",  # ✅ CRITICAL: Map "First Touch" to "first_touch"
        "Defending": "defending",
        "Goalkeeping": "goalkeeping",  # ✅ NEW: Add goalkeeping mapping
        "Fitness": "fitness",
    }
    
    return category_mapping.get(frontend_category, frontend_category.lower().replace(" ", "_"))


# ✅ NEW: Guest mode limited drills endpoint
@router.get("/public/drills/limited")
async def get_limited_drills_for_guests(db: Session = Depends(get_db)):
    """
    Get a limited, curated set of drills for guest users to try the app.
    Returns 7 drills each from key categories: Passing, Dribbling, Shooting, First Touch, Defending, Goalkeeping, Fitness.
    No authentication required.
    """
    try:
        logging.info("Fetching limited drills for guest mode")
        
        # Define the categories we want to showcase
        featured_categories = ["Passing", "Dribbling", "Shooting", "First Touch", "Defending", "Goalkeeping", "Fitness"]  # ✅ UPDATED: Add fitness
        
        all_guest_drills = []
        
        for category_name in featured_categories:
            # ✅ UPDATED: Map frontend category name to backend database name
            backend_category = map_frontend_category_to_backend(category_name)
            
            # Get drills for this category - reduced to 7 per category
            category_drills = db.query(Drill).join(DrillCategory).filter(
                DrillCategory.name.ilike(f"%{backend_category}%")
            ).limit(7).all()
            
            # Convert to response format
            for drill in category_drills:
                drill_response = drill_to_response(drill, db)
                all_guest_drills.append(drill_response)
        
        # Also add some general drills if we don't have enough (max 49 total - 7 categories * 7 drills)
        if len(all_guest_drills) < 49:
            general_drills = db.query(Drill).filter(
                ~Drill.id.in_([d["backend_id"] for d in all_guest_drills if "backend_id" in d])
            ).limit(7).all()
            
            for drill in general_drills:
                drill_response = drill_to_response(drill, db)
                all_guest_drills.append(drill_response)
        
        logging.info(f"Returning {len(all_guest_drills)} drills for guest mode")
        
        return {
            "drills": all_guest_drills,
            "total_count": len(all_guest_drills),
            "categories_included": featured_categories,
            "message": f"Limited drill selection for guest users - {len(all_guest_drills)} drills available. Sign up for access to 100+ drills!"
        }
        
    except Exception as e:
        logging.error(f"Error fetching limited drills for guests: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch guest drills: {str(e)}")


# ✅ NEW: Guest mode search with limits
@router.get("/public/drills/search/limited")
async def search_drills_for_guests(
    query: str = "",
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    page: int = 1,
    limit: int = 10,  # Reduced limit for guests
    db: Session = Depends(get_db)
):
    """
    Limited search endpoint for guest users.
    Returns smaller result sets to encourage account creation.
    When limit is high (>30), returns all available guest drills.
    """
    try:
        logging.info(f"Guest search: query='{query}', category='{category}', difficulty='{difficulty}', limit={limit}")
        
        # ✅ NEW: If limit is high, return all guest drills (for search page)
        if limit >= 30:
            # Get the full guest drill catalog from the limited endpoint
            all_guest_drills = []
            featured_categories = ["Passing", "Dribbling", "Shooting", "First Touch", "Defending", "Goalkeeping", "Fitness"]  # ✅ UPDATED: Add fitness
            
            for category_name in featured_categories:
                # ✅ UPDATED: Map frontend category name to backend database name
                backend_category = map_frontend_category_to_backend(category_name)
                
                category_drills = db.query(Drill).join(DrillCategory).filter(
                    DrillCategory.name.ilike(f"%{backend_category}%")
                ).limit(7).all()
                
                for drill in category_drills:
                    drill_response = drill_to_response(drill, db)
                    all_guest_drills.append(drill_response)
            
            # Apply search filters to the full guest catalog
            filtered_drills = all_guest_drills
            
            if query:
                filtered_drills = [
                    drill for drill in filtered_drills
                    if query.lower() in drill.get('title', '').lower() or
                       query.lower() in drill.get('description', '').lower()
                ]
            
            if category:
                # ✅ UPDATED: Map frontend category to backend for comparison
                backend_category = map_frontend_category_to_backend(category)
                
                # Find drills that match the category through their primary or secondary skills
                filtered_drills = [
                    drill for drill in filtered_drills
                    if (drill.get('primary_skill', {}).get('category', '').lower() == backend_category.lower() or
                        any(skill.get('category', '').lower() == backend_category.lower() 
                            for skill in drill.get('secondary_skills', [])))
                ]
            
            if difficulty:
                filtered_drills = [
                    drill for drill in filtered_drills
                    if drill.get('difficulty', '').lower() == difficulty.lower()
                ]
            
            logging.info(f"Returning {len(filtered_drills)} drills for guest search (all available)")
            
            return {
                "items": filtered_drills,
                "total": len(filtered_drills),
                "page": 1,
                "page_size": len(filtered_drills),
                "total_pages": 1,
                "has_next": False,
                "has_prev": False,
                "guest_mode": True,
                "message": f"Showing {len(filtered_drills)} of 49 available guest drills. Create an account for access to 100+ drills!"  # ✅ UPDATED: Update message to reflect 49 drills
            }
        
        # ✅ EXISTING: Standard pagination for smaller limits
        # Start with a base query
        drill_query = db.query(Drill)
        
        # Apply text search if provided
        if query:
            drill_query = drill_query.filter(
                or_(
                    Drill.title.ilike(f"%{query}%"),
                    Drill.description.ilike(f"%{query}%")
                )
            )
        
        # Apply category filter if provided
        if category:
            # ✅ UPDATED: Map frontend category name to backend database name
            backend_category = map_frontend_category_to_backend(category)
            drill_query = drill_query.join(DrillCategory).filter(
                DrillCategory.name.ilike(f"%{backend_category}%")
            )
        
        # Apply difficulty filter if provided
        if difficulty:
            drill_query = drill_query.filter(
                func.lower(Drill.difficulty) == difficulty.lower()
            )
        
        # Get total count but limit to guest maximum
        total = min(drill_query.count(), 28)  # Cap at 28 total results for guests
        
        # Apply pagination with guest limits
        drills = drill_query.offset((page - 1) * limit).limit(limit).all()
        
        # Convert to response format
        drill_responses = []
        for drill in drills[:limit]:  # Extra safety to ensure limit
            drill_responses.append(drill_to_response(drill, db))
        
        # Include pagination metadata with guest messaging
        response = {
            "items": drill_responses,
            "total": total,
            "page": page,
            "page_size": limit,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
            "guest_mode": True,
            "message": f"Showing {len(drill_responses)} of {total} drills for guest users. Create an account for access to 100+ drills!"
        }
        
        logging.info(f"Returning {len(drill_responses)} drills for guest search")
        
        return response
        
    except Exception as e:
        logging.error(f"Error in guest search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search drills for guest: {str(e)}")


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
            # ✅ UPDATED: Map frontend category name to backend database name
            backend_category = map_frontend_category_to_backend(category)
            drill_query = drill_query.join(DrillCategory).filter(
                DrillCategory.name.ilike(f"%{backend_category}%")
            )
        
        # Apply difficulty filter if provided
        if difficulty:
            drill_query = drill_query.filter(
                func.lower(Drill.difficulty) == difficulty.lower()
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