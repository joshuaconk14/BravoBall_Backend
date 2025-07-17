from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from models import User, DrillGroup, DrillResponse, DrillGroupRequest, DrillGroupResponse, DrillGroupItem, Drill, DrillSkillFocus
from db import get_db
from auth import get_current_user
import logging
from routers.router_utils import drill_to_response

router = APIRouter()


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
        for drill_uuid in group_data.drill_uuids:
            drill = db.query(Drill).filter(Drill.uuid == drill_uuid).first()
            if drill:
                # Add to junction table using UUID
                drill_item = DrillGroupItem(
                    drill_group_id=new_group.id,
                    drill_uuid=drill_uuid,  # Use UUID directly
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
        
        # Add new drill items using UUIDs
        position = 0
        for drill_uuid in group_data.drill_uuids:
            drill = db.query(Drill).filter(Drill.uuid == drill_uuid).first()
            if drill:
                drill_item = DrillGroupItem(
                    drill_group_id=existing_group.id,
                    drill_uuid=drill_uuid,  # Use UUID directly
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
@router.post("/api/drill-groups/{group_id}/drills/{drill_uuid}")
async def add_drill_to_group(
    group_id: int,
    drill_uuid: str,
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
        
        # Get the drill from the database using UUID
        drill = db.query(Drill).filter(Drill.uuid == drill_uuid).first()
        
        if not drill:
            raise HTTPException(status_code=404, detail="Drill not found")
        
        # Check if drill already in group using UUID
        existing_item = db.query(DrillGroupItem).filter(
            DrillGroupItem.drill_group_id == group_id,
            DrillGroupItem.drill_uuid == drill_uuid  # Use UUID instead of drill.id
        ).first()
        
        if existing_item:
            return {"message": "Drill already in group"}
        
        # Get highest position
        max_position = db.query(DrillGroupItem).filter(
            DrillGroupItem.drill_group_id == group_id
        ).count()
        
        # Add drill to group using UUID
        drill_item = DrillGroupItem(
            drill_group_id=group_id,
            drill_uuid=drill_uuid,  # Use UUID directly
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
@router.delete("/api/drill-groups/{group_id}/drills/{drill_uuid}")
async def remove_drill_from_group(
    group_id: int,
    drill_uuid: str,
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
        
        # Get the drill from the database using UUID
        drill = db.query(Drill).filter(Drill.uuid == drill_uuid).first()
        
        if not drill:
            raise HTTPException(status_code=404, detail="Drill not found")
        
        # Find and remove the drill from the group using UUID
        drill_item = db.query(DrillGroupItem).filter(
            DrillGroupItem.drill_group_id == group_id,
            DrillGroupItem.drill_uuid == drill_uuid  # Use UUID instead of drill.id
        ).first()
        
        if not drill_item:
            raise HTTPException(status_code=404, detail="Drill not found in group")
        
        db.delete(drill_item)
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

# Toggle like status for a drill
@router.post("/api/drills/{drill_uuid}/like")
async def toggle_drill_like(
    drill_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Toggle the like status of a drill (add/remove from liked drills).
    """
    try:
        # Get the drill from the database using UUID
        drill = db.query(Drill).filter(Drill.uuid == drill_uuid).first()
        
        if not drill:
            raise HTTPException(status_code=404, detail="Drill not found")
        
        # Get or create the user's liked drills group
        liked_group = db.query(DrillGroup).filter(
            DrillGroup.user_id == current_user.id,
            DrillGroup.is_liked_group == True
        ).first()
        
        if not liked_group:
            # Create liked drills group if it doesn't exist
            liked_group = DrillGroup(
                user_id=current_user.id,
                name="Liked Drills",
                description="Drills you've liked",
                is_liked_group=True
            )
            db.add(liked_group)
            db.flush()  # Get the ID without committing
        
        # Check if drill is already in liked group using UUID
        existing_item = db.query(DrillGroupItem).filter(
            DrillGroupItem.drill_group_id == liked_group.id,
            DrillGroupItem.drill_uuid == drill_uuid  # Use UUID instead of drill.id
        ).first()
        
        if existing_item:
            # Remove from liked group (unlike)
            db.delete(existing_item)
            message = "Drill unliked successfully"
            is_liked = False
        else:
            # Add to liked group (like)
            # Get highest position
            max_position = db.query(DrillGroupItem).filter(
                DrillGroupItem.drill_group_id == liked_group.id
            ).count()
            
            drill_item = DrillGroupItem(
                drill_group_id=liked_group.id,
                drill_uuid=drill_uuid,  # Use UUID directly
                position=max_position
            )
            db.add(drill_item)
            message = "Drill liked successfully"
            is_liked = True
        
        db.commit()
        
        return {
            "message": message,
            "is_liked": is_liked
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error toggling drill like: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle drill like: {str(e)}")

# Check if a drill is liked
@router.get("/api/drills/{drill_uuid}/like")
async def check_drill_liked(
    drill_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if a drill is in the user's liked drills group.
    """
    try:
        # Get the drill from the database using UUID
        drill = db.query(Drill).filter(Drill.uuid == drill_uuid).first()
        
        if not drill:
            raise HTTPException(status_code=404, detail="Drill not found")
        
        # Get the user's liked drills group
        liked_group = db.query(DrillGroup).filter(
            DrillGroup.user_id == current_user.id,
            DrillGroup.is_liked_group == True
        ).first()
        
        if not liked_group:
            return {"is_liked": False}
        
        # Check if drill is in liked group using UUID
        existing_item = db.query(DrillGroupItem).filter(
            DrillGroupItem.drill_group_id == liked_group.id,
            DrillGroupItem.drill_uuid == drill_uuid  # Use UUID instead of drill.id
        ).first()
        
        return {"is_liked": existing_item is not None}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error checking drill like status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to check drill like status: {str(e)}")

# Add multiple drills to a group at once
@router.post("/api/drill-groups/{group_id}/drills")
async def add_multiple_drills_to_group(
    group_id: int,
    drill_uuids: List[str],  # Changed from drill_ids to drill_uuids
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add multiple drills to a drill group at once.
    """
    try:
        # Get the drill group
        group = db.query(DrillGroup).filter(
            DrillGroup.id == group_id,
            DrillGroup.user_id == current_user.id
        ).first()
        
        if not group:
            raise HTTPException(status_code=404, detail="Drill group not found")
        
        # Get highest position
        max_position = db.query(DrillGroupItem).filter(
            DrillGroupItem.drill_group_id == group_id
        ).count()
        
        added_count = 0
        for drill_uuid in drill_uuids:
            # Get the drill from the database using UUID
            drill = db.query(Drill).filter(Drill.uuid == drill_uuid).first()
            
            if drill:
                # Check if drill already in group using UUID
                existing_item = db.query(DrillGroupItem).filter(
                    DrillGroupItem.drill_group_id == group_id,
                    DrillGroupItem.drill_uuid == drill_uuid  # Use UUID instead of drill.id
                ).first()
                
                if not existing_item:
                    # Add drill to group using UUID
                    drill_item = DrillGroupItem(
                        drill_group_id=group_id,
                        drill_uuid=drill_uuid,  # Use UUID directly
                        position=max_position + added_count
                    )
                    db.add(drill_item)
                    added_count += 1
        db.commit()
        
        return {
            "message": f"Added {added_count} drills to group successfully",
            "added_count": added_count
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error adding multiple drills to group: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add drills to group: {str(e)}")

# Also add a public endpoint to get all drill groups (without authentication)
@router.get("/public/drill-groups")
async def get_public_drill_groups(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all drill groups for a specific user without requiring authentication.
    This is useful for testing and debugging.
    """
    try:
        drill_groups = db.query(DrillGroup).filter(DrillGroup.user_id == user_id).all()
        
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

# Add multiple drills to liked drills at once
@router.post("/api/liked-drills/add")
async def add_multiple_drills_to_liked(
    drill_uuids: List[str],  # Changed from drill_ids to drill_uuids
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add multiple drills to the user's liked drills group at once.
    """
    try:
        # Get or create the user's liked drills group
        liked_group = db.query(DrillGroup).filter(
            DrillGroup.user_id == current_user.id,
            DrillGroup.is_liked_group == True
        ).first()
        
        if not liked_group:
            # Create liked drills group if it doesn't exist
            liked_group = DrillGroup(
                user_id=current_user.id,
                name="Liked Drills",
                description="Drills you've liked",
                is_liked_group=True
            )
            db.add(liked_group)
            db.flush()  # Get the ID without committing
        
        # Get highest position
        max_position = db.query(DrillGroupItem).filter(
            DrillGroupItem.drill_group_id == liked_group.id
        ).count()
        
        added_count = 0
        for drill_uuid in drill_uuids:
            # Get the drill from the database using UUID
            drill = db.query(Drill).filter(Drill.uuid == drill_uuid).first()
            
            if drill:
                # Check if drill already in liked group using UUID
                existing_item = db.query(DrillGroupItem).filter(
                    DrillGroupItem.drill_group_id == liked_group.id,
                    DrillGroupItem.drill_uuid == drill_uuid  # Use UUID instead of drill.id
                ).first()
                
                if not existing_item:
                    # Add drill to liked group using UUID
                    drill_item = DrillGroupItem(
                        drill_group_id=liked_group.id,
                        drill_uuid=drill_uuid,  # Use UUID directly
                        position=max_position + added_count
                    )
                    db.add(drill_item)
                    added_count += 1
        db.commit()
        
        return {
            "message": f"Added {added_count} drills to liked drills successfully",
            "added_count": added_count
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error adding multiple drills to liked: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add drills to liked: {str(e)}") 