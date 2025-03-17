from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from models import User, DrillGroup, DrillResponse, DrillGroupRequest, DrillGroupResponse, DrillGroupItem, Drill, DrillSkillFocus
from db import get_db
from auth import get_current_user
import logging

router = APIRouter()

# Helper function to convert Drill object to DrillResponse dict
def drill_to_response(drill, db):
    # Get the primary skill
    primary_skill = db.query(DrillSkillFocus).filter(
        DrillSkillFocus.drill_id == drill.id,
        DrillSkillFocus.is_primary == True
    ).first()
    
    # Get secondary skills
    secondary_skills = db.query(DrillSkillFocus).filter(
        DrillSkillFocus.drill_id == drill.id,
        DrillSkillFocus.is_primary == False
    ).all()
    
    return {
        "id": drill.id,
        "title": drill.title,
        "description": drill.description,
        "type": drill.type,
        "duration": drill.duration,
        "sets": drill.sets,
        "reps": drill.reps,
        "rest": drill.rest,
        "equipment": drill.equipment,
        "suitable_locations": drill.suitable_locations,
        "intensity": drill.intensity,
        "training_styles": drill.training_styles,
        "difficulty": drill.difficulty,
        "primary_skill": {
            "category": primary_skill.category,
            "sub_skill": primary_skill.sub_skill
        } if primary_skill else {},
        "secondary_skills": [
            {
                "category": skill.category,
                "sub_skill": skill.sub_skill
            }
            for skill in secondary_skills
        ],
        "instructions": drill.instructions,
        "tips": drill.tips,
        "common_mistakes": drill.common_mistakes,
        "progression_steps": drill.progression_steps,
        "variations": drill.variations,
        "video_url": drill.video_url,
        "thumbnail_url": drill.thumbnail_url
    }

# Get all drill groups for the current user
@router.get("/api/drill-groups/", response_model=List[DrillGroupResponse])
async def get_user_drill_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve all drill groups (collections) for the current user.
    """
    try:
        drill_groups = db.query(DrillGroup).filter(DrillGroup.user_id == current_user.id).all()
        
        # Convert to response format with drills array
        result = []
        for group in drill_groups:
            # Convert SQLAlchemy objects to DrillResponse format
            drills_data = [drill_to_response(drill, db) for drill in group.drills]
            
            # Create a copy of the group with drills added
            group_dict = {
                "id": group.id,
                "name": group.name,
                "description": group.description,
                "is_liked_group": group.is_liked_group,
                "drills": drills_data
            }
            result.append(group_dict)
            
        return result
    except Exception as e:
        logging.error(f"Error retrieving drill groups: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve drill groups: {str(e)}")

# Get a specific drill group by ID
@router.get("/api/drill-groups/{group_id}", response_model=DrillGroupResponse)
async def get_drill_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific drill group by its ID.
    """
    drill_group = db.query(DrillGroup).filter(
        DrillGroup.id == group_id,
        DrillGroup.user_id == current_user.id
    ).first()
    
    if not drill_group:
        raise HTTPException(status_code=404, detail="Drill group not found")
    
    # Convert to response format with drills array
    drills_data = [drill_to_response(drill, db) for drill in drill_group.drills]
    
    # Create response dict
    response = {
        "id": drill_group.id,
        "name": drill_group.name,
        "description": drill_group.description,
        "is_liked_group": drill_group.is_liked_group,
        "drills": drills_data
    }
    
    return response

# Create a new drill group
@router.post("/api/drill-groups/", response_model=DrillGroupResponse)
async def create_drill_group(
    group_data: DrillGroupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new drill group (saved collection) for the current user.
    """
    try:
        # Check if this is a "Liked Drills" group (only one allowed per user)
        if group_data.is_liked_group:
            existing_liked = db.query(DrillGroup).filter(
                DrillGroup.user_id == current_user.id,
                DrillGroup.is_liked_group == True
            ).first()
            
            if existing_liked:
                raise HTTPException(
                    status_code=400, 
                    detail="A 'Liked Drills' group already exists. You can only have one liked drills collection."
                )
        
        # Create new group without drills first
        new_group = DrillGroup(
            user_id=current_user.id,
            name=group_data.name,
            description=group_data.description,
            is_liked_group=group_data.is_liked_group
        )
        
        db.add(new_group)
        db.flush()  # Get the ID without committing
        
        # Add drills if provided
        position = 0
        for drill_id in group_data.drill_ids:
            drill = db.query(Drill).filter(Drill.id == drill_id).first()
            if drill:
                # Add to junction table
                drill_item = DrillGroupItem(
                    drill_group_id=new_group.id,
                    drill_id=drill_id,
                    position=position
                )
                db.add(drill_item)
                position += 1
        
        db.commit()
        db.refresh(new_group)
        
        # Convert to response format
        drills_data = [drill_to_response(drill, db) for drill in new_group.drills]
        
        # Create response dict
        response = {
            "id": new_group.id,
            "name": new_group.name,
            "description": new_group.description,
            "is_liked_group": new_group.is_liked_group,
            "drills": drills_data
        }
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error creating drill group: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create drill group: {str(e)}")

# Update an existing drill group
@router.put("/api/drill-groups/{group_id}", response_model=DrillGroupResponse)
async def update_drill_group(
    group_id: int,
    group_data: DrillGroupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing drill group.
    """
    try:
        # Get the existing group
        existing_group = db.query(DrillGroup).filter(
            DrillGroup.id == group_id,
            DrillGroup.user_id == current_user.id
        ).first()
        
        if not existing_group:
            raise HTTPException(status_code=404, detail="Drill group not found")
        
        # Check if we're trying to change a non-liked group to a liked group
        if not existing_group.is_liked_group and group_data.is_liked_group:
            # Check if user already has a liked drills group
            existing_liked = db.query(DrillGroup).filter(
                DrillGroup.user_id == current_user.id,
                DrillGroup.is_liked_group == True,
                DrillGroup.id != group_id  # Exclude current group
            ).first()
            
            if existing_liked:
                raise HTTPException(
                    status_code=400, 
                    detail="A 'Liked Drills' group already exists. You can only have one liked drills collection."
                )
        
        # Update group attributes
        existing_group.name = group_data.name
        existing_group.description = group_data.description
        existing_group.is_liked_group = group_data.is_liked_group
        
        # Remove all existing drill items
        db.query(DrillGroupItem).filter(DrillGroupItem.drill_group_id == existing_group.id).delete()
        
        # Add new drill items
        position = 0
        for drill_id in group_data.drill_ids:
            drill = db.query(Drill).filter(Drill.id == drill_id).first()
            if drill:
                drill_item = DrillGroupItem(
                    drill_group_id=existing_group.id,
                    drill_id=drill_id,
                    position=position
                )
                db.add(drill_item)
                position += 1
        
        db.commit()
        db.refresh(existing_group)
        
        # Convert to response format
        drills_data = [drill_to_response(drill, db) for drill in existing_group.drills]
        
        # Create response dict
        response = {
            "id": existing_group.id,
            "name": existing_group.name,
            "description": existing_group.description,
            "is_liked_group": existing_group.is_liked_group,
            "drills": drills_data
        }
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error updating drill group: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update drill group: {str(e)}")

# Delete a drill group
@router.delete("/api/drill-groups/{group_id}")
async def delete_drill_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a drill group.
    """
    existing_group = db.query(DrillGroup).filter(
        DrillGroup.id == group_id,
        DrillGroup.user_id == current_user.id
    ).first()
    
    if not existing_group:
        raise HTTPException(status_code=404, detail="Drill group not found")
    
    # Don't allow deletion of the Liked Drills group - it should always exist
    if existing_group.is_liked_group:
        raise HTTPException(
            status_code=400, 
            detail="The 'Liked Drills' group cannot be deleted. You can empty it instead."
        )
    
    try:
        db.delete(existing_group)
        db.commit()
        return {"message": "Drill group deleted successfully"}
    except Exception as e:
        db.rollback()
        logging.error(f"Error deleting drill group: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete drill group: {str(e)}")

# Add a drill to a group
@router.post("/api/drill-groups/{group_id}/drills/{drill_id}")
async def add_drill_to_group(
    group_id: int,
    drill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a single drill to a drill group.
    """
    try:
        # Get the drill group
        group = db.query(DrillGroup).filter(
            DrillGroup.id == group_id,
            DrillGroup.user_id == current_user.id
        ).first()
        
        if not group:
            raise HTTPException(status_code=404, detail="Drill group not found")
        
        # Get the drill from the database
        drill = db.query(Drill).filter(Drill.id == drill_id).first()
        
        if not drill:
            raise HTTPException(status_code=404, detail="Drill not found")
        
        # Check if drill already in group
        existing_item = db.query(DrillGroupItem).filter(
            DrillGroupItem.drill_group_id == group_id,
            DrillGroupItem.drill_id == drill_id
        ).first()
        
        if existing_item:
            return {"message": "Drill already in group"}
        
        # Get highest position
        max_position = db.query(DrillGroupItem).filter(
            DrillGroupItem.drill_group_id == group_id
        ).count()
        
        # Add drill to group
        drill_item = DrillGroupItem(
            drill_group_id=group_id,
            drill_id=drill_id,
            position=max_position
        )
        db.add(drill_item)
        db.commit()
        
        return {"message": "Drill added to group successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error adding drill to group: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add drill to group: {str(e)}")

# Remove a drill from a group
@router.delete("/api/drill-groups/{group_id}/drills/{drill_id}")
async def remove_drill_from_group(
    group_id: int,
    drill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a single drill from a drill group.
    """
    try:
        # Get the drill group
        group = db.query(DrillGroup).filter(
            DrillGroup.id == group_id,
            DrillGroup.user_id == current_user.id
        ).first()
        
        if not group:
            raise HTTPException(status_code=404, detail="Drill group not found")
        
        # Delete the drill group item
        result = db.query(DrillGroupItem).filter(
            DrillGroupItem.drill_group_id == group_id,
            DrillGroupItem.drill_id == drill_id
        ).delete()
        
        if result == 0:
            raise HTTPException(status_code=404, detail="Drill not found in this group")
        
        # Re-order remaining items
        items = db.query(DrillGroupItem).filter(
            DrillGroupItem.drill_group_id == group_id
        ).order_by(DrillGroupItem.position).all()
        
        for i, item in enumerate(items):
            item.position = i
        
        db.commit()
        
        return {"message": "Drill removed from group successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error removing drill from group: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to remove drill from group: {str(e)}")

# Create or get the Liked Drills group for a user
@router.get("/api/liked-drills", response_model=DrillGroupResponse)
async def get_liked_drills_group(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the user's Liked Drills collection, creating it if it doesn't exist.
    """
    try:
        # Try to find existing Liked Drills group
        liked_group = db.query(DrillGroup).filter(
            DrillGroup.user_id == current_user.id,
            DrillGroup.is_liked_group == True
        ).first()
        
        # If not found, create it
        if not liked_group:
            liked_group = DrillGroup(
                user_id=current_user.id,
                name="Liked Drills",
                description="Your collection of favorite drills",
                is_liked_group=True
            )
            db.add(liked_group)
            db.commit()
            db.refresh(liked_group)
        
        # Convert to response format
        drills_data = [drill_to_response(drill, db) for drill in liked_group.drills]
        
        # Create response dict
        response = {
            "id": liked_group.id,
            "name": liked_group.name,
            "description": liked_group.description,
            "is_liked_group": liked_group.is_liked_group,
            "drills": drills_data
        }
        
        return response
    except Exception as e:
        db.rollback()
        logging.error(f"Error getting liked drills group: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get liked drills group: {str(e)}")

# Like/unlike a drill (add to or remove from Liked Drills)
@router.post("/api/drills/{drill_id}/like")
async def toggle_drill_like(
    drill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Toggle a drill as liked/unliked. Adds or removes it from the Liked Drills group.
    """
    try:
        # Get or create the Liked Drills group
        liked_group = db.query(DrillGroup).filter(
            DrillGroup.user_id == current_user.id,
            DrillGroup.is_liked_group == True
        ).first()
        
        if not liked_group:
            liked_group = DrillGroup(
                user_id=current_user.id,
                name="Liked Drills",
                description="Your collection of favorite drills",
                is_liked_group=True
            )
            db.add(liked_group)
            db.commit()
            db.refresh(liked_group)
        
        # Check if drill exists
        drill = db.query(Drill).filter(Drill.id == drill_id).first()
        if not drill:
            raise HTTPException(status_code=404, detail="Drill not found")
        
        # Check if drill already in liked group
        existing_item = db.query(DrillGroupItem).filter(
            DrillGroupItem.drill_group_id == liked_group.id,
            DrillGroupItem.drill_id == drill_id
        ).first()
        
        if existing_item:
            # Drill is already liked, so unlike it
            db.delete(existing_item)
            db.commit()
            return {"message": "Drill unliked successfully", "is_liked": False}
        
        # Get highest position
        max_position = db.query(DrillGroupItem).filter(
            DrillGroupItem.drill_group_id == liked_group.id
        ).count()
        
        # Add drill to liked group
        drill_item = DrillGroupItem(
            drill_group_id=liked_group.id,
            drill_id=drill_id,
            position=max_position
        )
        db.add(drill_item)
        db.commit()
        
        return {"message": "Drill liked successfully", "is_liked": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error toggling drill like: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle drill like: {str(e)}")

# Check if a drill is liked
@router.get("/api/drills/{drill_id}/like")
async def check_drill_liked(
    drill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if a drill is in the user's Liked Drills collection.
    """
    try:
        # Get the Liked Drills group
        liked_group = db.query(DrillGroup).filter(
            DrillGroup.user_id == current_user.id,
            DrillGroup.is_liked_group == True
        ).first()
        
        # If liked group doesn't exist, drill is not liked
        if not liked_group:
            return {"is_liked": False}
        
        # Check if drill is in liked group
        is_liked = db.query(DrillGroupItem).filter(
            DrillGroupItem.drill_group_id == liked_group.id,
            DrillGroupItem.drill_id == drill_id
        ).first() is not None
        
        return {"is_liked": is_liked}
    except Exception as e:
        logging.error(f"Error checking if drill is liked: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to check if drill is liked: {str(e)}") 