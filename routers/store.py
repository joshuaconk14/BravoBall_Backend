"""
store.py
Endpoints for managing user store items (treats, streak freezes, streak revivers)
RevenueCat handles all transactions - these endpoints just manage item quantities
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date
from models import User, UserStoreItems, ProgressHistory
from schemas import UserStoreItemsResponse, UserStoreItemsUpdate, ProgressHistoryResponse
from db import get_db
from auth import get_current_user

router = APIRouter()


@router.get("/api/store/items", response_model=UserStoreItemsResponse)
async def get_user_store_items(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's store items inventory
    """
    try:
        # Get or create store items for user
        store_items = db.query(UserStoreItems).filter(
            UserStoreItems.user_id == current_user.id
        ).first()
        
        if not store_items:
            # Create default store items if they don't exist
            store_items = UserStoreItems(
                user_id=current_user.id,
                treats=0,
                streak_freezes=0,
                streak_revivers=0,
                used_freezes=[]
            )
            db.add(store_items)
            db.commit()
            db.refresh(store_items)
        else:
            # Ensure used_freezes is initialized for existing records
            if store_items.used_freezes is None:
                store_items.used_freezes = []
                db.commit()
                db.refresh(store_items)
        
        return store_items
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get store items: {str(e)}"
        )


@router.put("/api/store/items", response_model=UserStoreItemsResponse)
async def update_user_store_items(
    items_update: UserStoreItemsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the user's store items inventory
    This should be called after RevenueCat confirms a successful purchase
    
    Only updates the fields that are provided (non-None values)
    """
    try:
        # Get or create store items for user
        store_items = db.query(UserStoreItems).filter(
            UserStoreItems.user_id == current_user.id
        ).first()
        
        if not store_items:
            # Create new store items record
            store_items = UserStoreItems(
                user_id=current_user.id,
                treats=items_update.treats if items_update.treats is not None else 0,
                streak_freezes=items_update.streak_freezes if items_update.streak_freezes is not None else 0,
                streak_revivers=items_update.streak_revivers if items_update.streak_revivers is not None else 0
            )
            db.add(store_items)
        else:
            # Update only the fields that are provided
            if items_update.treats is not None:
                store_items.treats = items_update.treats
            if items_update.streak_freezes is not None:
                store_items.streak_freezes = items_update.streak_freezes
            if items_update.streak_revivers is not None:
                store_items.streak_revivers = items_update.streak_revivers
        
        db.commit()
        db.refresh(store_items)
        
        return store_items
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update store items: {str(e)}"
        )


@router.post("/api/store/items/increment", response_model=UserStoreItemsResponse)
async def increment_store_items(
    items_update: UserStoreItemsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Increment store items by the specified amounts
    Use this endpoint after a successful purchase from RevenueCat
    
    Example: If user has 5 treats and you send treats=3, they'll have 8 treats
    """
    try:
        # Get or create store items for user
        store_items = db.query(UserStoreItems).filter(
            UserStoreItems.user_id == current_user.id
        ).first()
        
        if not store_items:
            # Create new store items record with the increment values
            store_items = UserStoreItems(
                user_id=current_user.id,
                treats=items_update.treats if items_update.treats is not None else 0,
                streak_freezes=items_update.streak_freezes if items_update.streak_freezes is not None else 0,
                streak_revivers=items_update.streak_revivers if items_update.streak_revivers is not None else 0
            )
            db.add(store_items)
        else:
            # Increment the values
            if items_update.treats is not None:
                store_items.treats += items_update.treats
            if items_update.streak_freezes is not None:
                store_items.streak_freezes += items_update.streak_freezes
            if items_update.streak_revivers is not None:
                store_items.streak_revivers += items_update.streak_revivers
        
        db.commit()
        db.refresh(store_items)
        
        return store_items
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to increment store items: {str(e)}"
        )


@router.post("/api/store/items/decrement", response_model=UserStoreItemsResponse)
async def decrement_store_items(
    items_update: UserStoreItemsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Decrement store items by the specified amounts
    Use this endpoint when a user uses/consumes an item
    
    Example: If user has 5 treats and you send treats=1, they'll have 4 treats
    Note: Values cannot go below 0
    """
    try:
        # Get store items for user
        store_items = db.query(UserStoreItems).filter(
            UserStoreItems.user_id == current_user.id
        ).first()
        
        if not store_items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User has no store items to decrement"
            )
        
        # Decrement the values (but don't go below 0)
        if items_update.treats is not None:
            store_items.treats = max(0, store_items.treats - items_update.treats)
        if items_update.streak_freezes is not None:
            store_items.streak_freezes = max(0, store_items.streak_freezes - items_update.streak_freezes)
        if items_update.streak_revivers is not None:
            store_items.streak_revivers = max(0, store_items.streak_revivers - items_update.streak_revivers)
        
        db.commit()
        db.refresh(store_items)
        
        return store_items
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decrement store items: {str(e)}"
        )


@router.post("/api/store/use-streak-reviver")
async def use_streak_reviver(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Use a streak reviver to restore a lost streak
    
    This endpoint:
    - Checks if the user has streak revivers available
    - Checks if the user has a lost streak to restore (current_streak == 0 and previous_streak > 0)
    - Restores the previous streak to current_streak
    - Decrements streak_revivers by 1
    
    Returns:
        Updated progress history and store items
    """
    try:
        # Get user's store items
        store_items = db.query(UserStoreItems).filter(
            UserStoreItems.user_id == current_user.id
        ).first()
        
        if not store_items or store_items.streak_revivers <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You don't have any streak revivers available"
            )
        
        # Get user's progress history
        progress_history = db.query(ProgressHistory).filter(
            ProgressHistory.user_id == current_user.id
        ).first()
        
        if not progress_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Progress history not found"
            )
        
        # Check if there's a lost streak to restore
        if progress_history.current_streak > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active streak. Streak revivers can only be used when you've lost your streak."
            )
        
        if progress_history.previous_streak <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You don't have a previous streak to restore"
            )
        
        # Restore the streak
        progress_history.current_streak = progress_history.previous_streak
        progress_history.previous_streak = 0
        
        # Decrement streak revivers
        store_items.streak_revivers -= 1
        
        db.commit()
        db.refresh(progress_history)
        db.refresh(store_items)
        
        return {
            "success": True,
            "message": f"Streak revived! Your {progress_history.current_streak}-day streak has been restored.",
            "progress_history": {
                "current_streak": progress_history.current_streak,
                "previous_streak": progress_history.previous_streak
            },
            "store_items": {
                "streak_revivers": store_items.streak_revivers
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to use streak reviver: {str(e)}"
        )


@router.post("/api/store/use-streak-freeze")
async def use_streak_freeze(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Use a streak freeze to protect today's streak
    
    This endpoint:
    - Checks if the user has streak freezes available
    - Checks if the user has an active streak (current_streak > 0)
    - Sets active_freeze_date to TODAY
    - Decrements streak_freezes by 1
    - Prevents the streak from breaking if user doesn't train today
    
    Returns:
        Updated progress history and store items
    """
    try:
        # Get user's store items
        store_items = db.query(UserStoreItems).filter(
            UserStoreItems.user_id == current_user.id
        ).first()
        
        if not store_items or store_items.streak_freezes <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You don't have any streak freezes available"
            )
        
        # Get user's progress history
        progress_history = db.query(ProgressHistory).filter(
            ProgressHistory.user_id == current_user.id
        ).first()
        
        if not progress_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Progress history not found"
            )
        
        # Check if user has an active streak
        if progress_history.current_streak <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You need an active streak to use a streak freeze"
            )
        
        # Check if there's already an active freeze
        today = datetime.now().date()
        if store_items.active_freeze_date:
            if store_items.active_freeze_date == today:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You already have a streak freeze active for today"
                )
            # Clear expired freeze dates (older than today)
            elif store_items.active_freeze_date < today:
                store_items.active_freeze_date = None
        
        # Activate freeze for today
        store_items.active_freeze_date = today
        
        # Add to used freezes history
        if store_items.used_freezes is None:
            store_items.used_freezes = []
        store_items.used_freezes.append(today.isoformat())
        
        # Decrement streak freezes
        store_items.streak_freezes -= 1
        
        db.commit()
        db.refresh(store_items)
        
        return {
            "success": True,
            "message": f"Streak freeze activated for today! Your {progress_history.current_streak}-day streak is protected.",
            "freeze_date": today.isoformat(),
            "progress_history": {
                "current_streak": progress_history.current_streak
            },
            "store_items": {
                "streak_freezes": store_items.streak_freezes,
                "active_freeze_date": store_items.active_freeze_date.isoformat() if store_items.active_freeze_date else None,
                "used_freezes": store_items.used_freezes
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to use streak freeze: {str(e)}"
        )



