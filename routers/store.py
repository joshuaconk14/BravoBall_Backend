"""
store.py
Endpoints for managing user store items (treats, streak freezes, streak revivers)
RevenueCat handles all transactions - these endpoints just manage item quantities
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional
import httpx
from models import User, UserStoreItems, ProgressHistory, PurchaseTransaction
from schemas import (
    UserStoreItemsResponse, 
    UserStoreItemsUpdate, 
    ProgressHistoryResponse,
    VerifyTreatPurchaseRequest,
    VerifyTreatPurchaseResponse
)
from db import get_db
from auth import get_current_user
from config import RevenueCat

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
                used_freezes=[],
                used_revivers=[]
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
        
        # Track reviver usage
        today = datetime.now().date()
        store_items.active_streak_reviver = today
        
        # Add to used revivers history
        if store_items.used_revivers is None:
            store_items.used_revivers = []
        store_items.used_revivers.append(today.isoformat())
        
        # Decrement streak revivers
        store_items.streak_revivers -= 1
        
        # ✅ IMPORTANT: Flag the JSON field as modified so SQLAlchemy saves it
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(store_items, 'used_revivers')
        
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
                "streak_revivers": store_items.streak_revivers,
                "active_streak_reviver": store_items.active_streak_reviver.isoformat() if store_items.active_streak_reviver else None,
                "used_revivers": store_items.used_revivers
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
        
        # ✅ IMPORTANT: Flag the JSON field as modified so SQLAlchemy saves it
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(store_items, 'used_freezes')
        
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
                "used_freezes": store_items.used_freezes,
                "active_streak_reviver": store_items.active_streak_reviver.isoformat() if store_items.active_streak_reviver else None,
                "used_revivers": store_items.used_revivers
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


# Helper Functions for Purchase Verification
async def verify_with_revenuecat_api(revenue_cat_user_id: str, platform: str) -> dict:
    """
    Fetch customer info from RevenueCat API to verify purchase
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{RevenueCat.API_URL}/subscribers/{revenue_cat_user_id}",
            headers={
                "Authorization": f"Bearer {RevenueCat.API_KEY}",
                "X-Platform": platform.lower()  # 'ios' or 'android'
            },
            timeout=10.0
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to verify with RevenueCat: {response.status_code}"
            )
        
        return response.json()


def transaction_exists_in_customer_info(
    customer_info: dict, 
    transaction_id: str, 
    product_id: str
) -> bool:
    """
    Check if transaction exists in RevenueCat customer info
    """
    # Check non-subscription transactions
    subscriber = customer_info.get("subscriber", {})
    non_subscription_transactions = subscriber.get("non_subscriptions", {})
    
    # Look for the product_id in transactions
    for product_key, transactions in non_subscription_transactions.items():
        if product_key == product_id:
            # Check if transaction_id exists in this product's transactions
            for transaction in transactions:
                if transaction.get("id") == transaction_id:
                    return True
    
    return False


def transaction_already_processed(
    db: Session,
    transaction_id: str
) -> bool:
    """
    Check if transaction was already processed (idempotency check)
    """
    existing = db.query(PurchaseTransaction).filter(
        PurchaseTransaction.transaction_id == transaction_id
    ).first()
    
    return existing is not None


def grant_treats_to_user(
    db: Session,
    user_id: int,
    treat_amount: int
) -> UserStoreItems:
    """
    Grant treats to user by incrementing their treat balance
    """
    store_items = db.query(UserStoreItems).filter(
        UserStoreItems.user_id == user_id
    ).first()
    
    if not store_items:
        # Create new store items record
        store_items = UserStoreItems(
            user_id=user_id,
            treats=treat_amount,
            streak_freezes=0,
            streak_revivers=0,
            used_freezes=[],
            used_revivers=[]
        )
        db.add(store_items)
    else:
        # Increment existing treats
        store_items.treats += treat_amount
    
    db.commit()
    db.refresh(store_items)
    return store_items


def store_transaction(
    db: Session,
    transaction_id: str,
    user_id: int,
    treat_amount: int,
    product_id: str,
    platform: str,
    original_transaction_id: Optional[str] = None
) -> PurchaseTransaction:
    """
    Store transaction record for idempotency
    """
    transaction = PurchaseTransaction(
        user_id=user_id,
        transaction_id=transaction_id,
        original_transaction_id=original_transaction_id,
        product_id=product_id,
        treat_amount=treat_amount,
        platform=platform,
        processed_at=datetime.utcnow()
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_user_store_items(db: Session, user_id: int) -> UserStoreItems:
    """
    Get user's store items, creating if doesn't exist
    """
    store_items = db.query(UserStoreItems).filter(
        UserStoreItems.user_id == user_id
    ).first()
    
    if not store_items:
        store_items = UserStoreItems(
            user_id=user_id,
            treats=0,
            streak_freezes=0,
            streak_revivers=0,
            used_freezes=[],
            used_revivers=[]
        )
        db.add(store_items)
        db.commit()
        db.refresh(store_items)
    
    return store_items


# Purchase Verification Endpoint
@router.post("/api/store/verify-treat-purchase", response_model=VerifyTreatPurchaseResponse)
async def verify_treat_purchase(
    request_data: VerifyTreatPurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify purchase directly with RevenueCat API and grant treats
    
    This endpoint:
    - Verifies the purchase with RevenueCat API
    - Checks if transaction exists in RevenueCat customer info
    - Prevents duplicate processing (idempotency)
    - Grants treats to the user
    - Records the transaction
    """
    try:
        # 1. Verify with RevenueCat API
        customer_info = await verify_with_revenuecat_api(
            request_data.revenue_cat_user_id,
            request_data.platform
        )
        
        # 2. Check if transaction exists in customer_info
        if not transaction_exists_in_customer_info(
            customer_info, 
            request_data.transaction_id, 
            request_data.product_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction not found in RevenueCat"
            )
        
        # 3. Check for duplicate (idempotency)
        if transaction_already_processed(db, request_data.transaction_id):
            # Already processed, return current balance
            store_items = get_user_store_items(db, current_user.id)
            return VerifyTreatPurchaseResponse(
                success=True,
                treats=store_items.treats,
                message="Transaction already processed"
            )
        
        # 4. Grant treats
        store_items = grant_treats_to_user(
            db,
            current_user.id,
            request_data.treat_amount
        )
        
        # 5. Record transaction
        store_transaction(
            db,
            request_data.transaction_id,
            current_user.id,
            request_data.treat_amount,
            request_data.product_id,
            request_data.platform,
            request_data.original_transaction_id
        )
        
        # 6. Return success
        return VerifyTreatPurchaseResponse(
            success=True,
            treats=store_items.treats,
            message="Purchase verified and treats granted"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify purchase: {str(e)}"
        )


