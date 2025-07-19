from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import User, CustomDrill, CustomDrillCreate, CustomDrillResponse
from db import get_db
from auth import get_current_user
import logging

router = APIRouter()

@router.post("/api/custom-drills/", response_model=CustomDrillResponse)
async def create_custom_drill(
    drill_data: CustomDrillCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Create the custom drill
        custom_drill = CustomDrill(
            user_id=current_user.id,
            title=drill_data.title,
            description=drill_data.description,
            type=drill_data.type,
            duration=drill_data.duration,
            sets=drill_data.sets,
            reps=drill_data.reps,
            rest=drill_data.rest,
            equipment=drill_data.equipment,
            suitable_locations=drill_data.suitable_locations,
            intensity=drill_data.intensity,
            training_styles=drill_data.training_styles,
            difficulty=drill_data.difficulty,
            primary_skill=drill_data.primary_skill,
            instructions=drill_data.instructions,
            tips=drill_data.tips,
            common_mistakes=drill_data.common_mistakes,
            progression_steps=drill_data.progression_steps,
            variations=drill_data.variations,
            video_url=drill_data.video_url,
            thumbnail_url=drill_data.thumbnail_url,
            is_custom=True  # ✅ Set to True for custom drills
        )
        
        db.add(custom_drill)
        db.commit()
        db.refresh(custom_drill)
        
        # Convert to response format
        response = CustomDrillResponse(
            uuid=str(custom_drill.uuid),
            title=custom_drill.title,
            description=custom_drill.description,
            type=custom_drill.type,
            duration=custom_drill.duration,
            sets=custom_drill.sets,
            reps=custom_drill.reps,
            rest=custom_drill.rest,
            equipment=custom_drill.equipment,
            suitable_locations=custom_drill.suitable_locations,
            intensity=custom_drill.intensity,
            training_styles=custom_drill.training_styles,
            difficulty=custom_drill.difficulty,
            primary_skill=custom_drill.primary_skill,
            instructions=custom_drill.instructions,
            tips=custom_drill.tips,
            common_mistakes=custom_drill.common_mistakes,
            progression_steps=custom_drill.progression_steps,
            variations=custom_drill.variations,
            video_url=custom_drill.video_url,
            thumbnail_url=custom_drill.thumbnail_url,
            created_at=custom_drill.created_at.isoformat() if custom_drill.created_at else None,
            updated_at=custom_drill.updated_at.isoformat() if custom_drill.updated_at else None
        )
        
        return response
        
    except Exception as e:
        db.rollback()
        logging.error(f"Error creating custom drill: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create custom drill: {str(e)}"
        )

@router.get("/api/custom-drills/", response_model=List[CustomDrillResponse])
async def get_user_custom_drills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        custom_drills = db.query(CustomDrill).filter(
            CustomDrill.user_id == current_user.id
        ).order_by(CustomDrill.created_at.desc()).all()
        
        # Convert to response format
        response = []
        for drill in custom_drills:
            drill_response = CustomDrillResponse(
                uuid=str(drill.uuid),
                title=drill.title,
                description=drill.description,
                type=drill.type,
                duration=drill.duration,
                sets=drill.sets,
                reps=drill.reps,
                rest=drill.rest,
                equipment=drill.equipment,
                suitable_locations=drill.suitable_locations,
                intensity=drill.intensity,
                training_styles=drill.training_styles,
                difficulty=drill.difficulty,
                primary_skill=drill.primary_skill,
                instructions=drill.instructions,
                tips=drill.tips,
                common_mistakes=drill.common_mistakes,
                progression_steps=drill.progression_steps,
                variations=drill.variations,
                video_url=drill.video_url,
                thumbnail_url=drill.thumbnail_url,
                created_at=drill.created_at.isoformat() if drill.created_at else None,
                updated_at=drill.updated_at.isoformat() if drill.updated_at else None,
                is_custom=drill.is_custom
            )
            response.append(drill_response)
        
        return response
        
    except Exception as e:
        logging.error(f"Error getting custom drills: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get custom drills: {str(e)}"
        )

@router.get("/api/custom-drills/{drill_uuid}", response_model=CustomDrillResponse)
async def get_custom_drill(
    drill_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        custom_drill = db.query(CustomDrill).filter(
            CustomDrill.uuid == drill_uuid,
            CustomDrill.user_id == current_user.id
        ).first()
        
        if not custom_drill:
            raise HTTPException(
                status_code=404, detail="Custom drill not found"
            )
        
        # Convert to response format
        response = CustomDrillResponse(
            uuid=str(custom_drill.uuid),
            title=custom_drill.title,
            description=custom_drill.description,
            type=custom_drill.type,
            duration=custom_drill.duration,
            sets=custom_drill.sets,
            reps=custom_drill.reps,
            rest=custom_drill.rest,
            equipment=custom_drill.equipment,
            suitable_locations=custom_drill.suitable_locations,
            intensity=custom_drill.intensity,
            training_styles=custom_drill.training_styles,
            difficulty=custom_drill.difficulty,
            primary_skill=custom_drill.primary_skill,
            instructions=custom_drill.instructions,
            tips=custom_drill.tips,
            common_mistakes=custom_drill.common_mistakes,
            progression_steps=custom_drill.progression_steps,
            variations=custom_drill.variations,
            video_url=custom_drill.video_url,
            thumbnail_url=custom_drill.thumbnail_url,
            created_at=custom_drill.created_at.isoformat() if custom_drill.created_at else None,
            updated_at=custom_drill.updated_at.isoformat() if custom_drill.updated_at else None,
            is_custom=custom_drill.is_custom
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting custom drill: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get custom drill: {str(e)}"
        )

@router.put("/api/custom-drills/{drill_uuid}", response_model=CustomDrillResponse)
async def update_custom_drill(
    drill_uuid: str,
    drill_data: CustomDrillCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        custom_drill = db.query(CustomDrill).filter(
            CustomDrill.uuid == drill_uuid,
            CustomDrill.user_id == current_user.id
        ).first()
        
        if not custom_drill:
            raise HTTPException(
                status_code=404, detail="Custom drill not found"
            )
        
        # Update the drill fields
        custom_drill.title = drill_data.title
        custom_drill.description = drill_data.description
        custom_drill.type = drill_data.type
        custom_drill.duration = drill_data.duration
        custom_drill.sets = drill_data.sets
        custom_drill.reps = drill_data.reps
        custom_drill.rest = drill_data.rest
        custom_drill.equipment = drill_data.equipment
        custom_drill.suitable_locations = drill_data.suitable_locations
        custom_drill.intensity = drill_data.intensity
        custom_drill.training_styles = drill_data.training_styles
        custom_drill.difficulty = drill_data.difficulty
        custom_drill.primary_skill = drill_data.primary_skill
        custom_drill.instructions = drill_data.instructions
        custom_drill.tips = drill_data.tips
        custom_drill.common_mistakes = drill_data.common_mistakes
        custom_drill.progression_steps = drill_data.progression_steps
        custom_drill.variations = drill_data.variations
        custom_drill.video_url = drill_data.video_url
        custom_drill.thumbnail_url = drill_data.thumbnail_url
        
        db.commit()
        db.refresh(custom_drill)
        
        # Convert to response format
        response = CustomDrillResponse(
            uuid=str(custom_drill.uuid),
            title=custom_drill.title,
            description=custom_drill.description,
            type=custom_drill.type,
            duration=custom_drill.duration,
            sets=custom_drill.sets,
            reps=custom_drill.reps,
            rest=custom_drill.rest,
            equipment=custom_drill.equipment,
            suitable_locations=custom_drill.suitable_locations,
            intensity=custom_drill.intensity,
            training_styles=custom_drill.training_styles,
            difficulty=custom_drill.difficulty,
            primary_skill=custom_drill.primary_skill,
            instructions=custom_drill.instructions,
            tips=custom_drill.tips,
            common_mistakes=custom_drill.common_mistakes,
            progression_steps=custom_drill.progression_steps,
            variations=custom_drill.variations,
            video_url=custom_drill.video_url,
            thumbnail_url=custom_drill.thumbnail_url,
            created_at=custom_drill.created_at.isoformat() if custom_drill.created_at else None,
            updated_at=custom_drill.updated_at.isoformat() if custom_drill.updated_at else None
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error updating custom drill: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update custom drill: {str(e)}"
        )

@router.patch("/api/custom-drills/{drill_uuid}/")
async def update_custom_drill_video(
    drill_uuid: str,
    video_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update only the video URL of a custom drill.
    Expects a JSON body with 'video_url' field.
    """
    try:
        custom_drill = db.query(CustomDrill).filter(
            CustomDrill.uuid == drill_uuid,
            CustomDrill.user_id == current_user.id
        ).first()
        
        if not custom_drill:
            raise HTTPException(
                status_code=404, detail="Custom drill not found"
            )
        
        # Update only the video URL
        if 'video_url' in video_data:
            custom_drill.video_url = video_data['video_url']
            logging.info(f"Updating video URL for drill {drill_uuid} to: {video_data['video_url']}")
        
        db.commit()
        db.refresh(custom_drill)
        
        return {
            "message": "Video updated successfully",
            "video_url": custom_drill.video_url,
            "drill_uuid": str(custom_drill.uuid)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error updating custom drill video: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update custom drill video: {str(e)}"
        )

@router.delete("/api/custom-drills/{drill_uuid}/")
async def delete_custom_drill(
    drill_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        custom_drill = db.query(CustomDrill).filter(
            CustomDrill.uuid == drill_uuid,
            CustomDrill.user_id == current_user.id
        ).first()
        
        if not custom_drill:
            raise HTTPException(
                status_code=404, detail="Custom drill not found"
            )
        
        db.delete(custom_drill)
        db.commit()
        
        return {"message": "Custom drill deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error deleting custom drill: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete custom drill: {str(e)}"
        ) 