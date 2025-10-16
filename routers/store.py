"""
store.py
Endpoints for managing user store items (treats, streak freezes, streak revivers)
RevenueCat handles all transactions - these endpoints just manage item quantities
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import User, UserStoreItems
from schemas import UserStoreItemsResponse, UserStoreItemsUpdate
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
                streak_revivers=0
            )
            db.add(store_items)
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

