"""
store.py
Endpoints for managing user store items (treats, streak freezes, streak revivers)
RevenueCat handles all transactions - these endpoints just manage item quantities
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date
from typing import Optional
import httpx
import json
import asyncio
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
from config import RevenueCat, get_logger

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
    
    RevenueCat stores transactions in:
    1. non_subscriptions - for regular one-time purchases
    2. other_purchases - for StoreKit simulator/test purchases
    
    Structure:
    {
      "product_id": [
        {
          "id": "transaction_id",
          "is_sandbox": true/false,
          "original_purchase_date": "...",
          "purchase_date": "..."
        }
      ]
    }
    """
    logger = get_logger(__name__)
    
    # Ensure customer_info is a dict
    if not isinstance(customer_info, dict):
        logger.error(f"Invalid customer_info type: {type(customer_info)}")
        return False
    
    subscriber = customer_info.get("subscriber", {})
    
    # Ensure subscriber is a dict
    if not isinstance(subscriber, dict):
        logger.error(f"Invalid subscriber type: {type(subscriber)}")
        return False
    
    # Log for debugging
    logger.info(f"Looking for transaction_id: {transaction_id}, product_id: {product_id}")
    
    # Helper function to check transactions in a dictionary
    def check_transactions_in_dict(transactions_dict: dict, source_name: str) -> bool:
        """Check if transaction exists in a transactions dictionary"""
        if not transactions_dict or not isinstance(transactions_dict, dict):
            logger.info(f"No transactions found in {source_name}")
            return False
        
        logger.info(f"Available products in {source_name}: {list(transactions_dict.keys())}")
        
        # Look for the product_id in transactions
        for product_key, transactions in transactions_dict.items():
            # Ensure transactions is a list/iterable
            if not isinstance(transactions, (list, tuple)):
                logger.warning(f"Transactions for product {product_key} is not a list: {type(transactions)}")
                continue
            
            logger.info(f"Checking product: {product_key}, has {len(transactions)} transactions")
            
            # Try exact match first
            if product_key == product_id:
                # Check if transaction_id exists in this product's transactions
                for transaction in transactions:
                    # Handle case where transaction might be a dict or string
                    if isinstance(transaction, dict):
                        # Try multiple possible field names for transaction ID
                        trans_id = (
                            transaction.get("id") or 
                            transaction.get("transaction_id") or 
                            transaction.get("original_transaction_id")
                        )
                    elif isinstance(transaction, str):
                        # Transaction might be stored as a string ID directly
                        trans_id = transaction
                    else:
                        logger.warning(f"Unexpected transaction type in {source_name}: {type(transaction)}")
                        continue
                    
                    logger.info(f"  Transaction ID in RevenueCat ({source_name}): {trans_id}")
                    if trans_id == transaction_id:
                        logger.info(f"✅ Found matching transaction in {source_name}!")
                        return True
            
            # Also check if product_id is a substring match (for package identifiers)
            if product_id in product_key or product_key in product_id:
                logger.info(f"Product ID partial match: {product_key} vs {product_id}")
                for transaction in transactions:
                    # Handle case where transaction might be a dict or string
                    if isinstance(transaction, dict):
                        trans_id = (
                            transaction.get("id") or 
                            transaction.get("transaction_id") or 
                            transaction.get("original_transaction_id")
                        )
                    elif isinstance(transaction, str):
                        trans_id = transaction
                    else:
                        continue
                    
                    if trans_id == transaction_id:
                        logger.info(f"✅ Found matching transaction with partial product match in {source_name}!")
                        return True
        
        return False
    
    # Check non_subscriptions first (regular purchases)
    non_subscription_transactions = subscriber.get("non_subscriptions", {})
    if check_transactions_in_dict(non_subscription_transactions, "non_subscriptions"):
        return True
    
    # Check other_purchases (StoreKit simulator/test purchases)
    other_purchases = subscriber.get("other_purchases", {})
    if check_transactions_in_dict(other_purchases, "other_purchases"):
        return True
    
    # If not found, log full structure for debugging
    logger.warning("Transaction not found in non_subscriptions or other_purchases")
    logger.info(f"Full subscriber structure keys: {list(subscriber.keys())}")
    
    # Log the actual content (not just debug level)
    logger.info(f"non_subscriptions content: {json.dumps(non_subscription_transactions, indent=2, default=str)}")
    logger.info(f"other_purchases content: {json.dumps(other_purchases, indent=2, default=str)}")
    
    # Check if there are any transactions in entitlements (sometimes purchases show up there)
    entitlements = subscriber.get("entitlements", {})
    if entitlements:
        logger.info(f"Found entitlements: {list(entitlements.keys())}")
        for entitlement_key, entitlement_data in entitlements.items():
            logger.info(f"  Entitlement: {entitlement_key}, product_identifier: {entitlement_data.get('product_identifier')}")
    
    # Log full subscriber for deep debugging (truncated if too large)
    full_subscriber_str = json.dumps(subscriber, indent=2, default=str)
    if len(full_subscriber_str) > 2000:
        logger.info(f"Full subscriber structure (truncated): {full_subscriber_str[:2000]}...")
    else:
        logger.info(f"Full subscriber structure: {full_subscriber_str}")
    
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
    
    NOTE: Does NOT commit - caller must commit for atomicity.
    Use db.flush() to get updated value without committing.
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
    
    # Flush to get updated value without committing
    # Caller will handle the commit for atomicity
    db.flush()
    db.refresh(store_items)
    return store_items


def store_transaction(
    db: Session,
    transaction_id: str,
    user_id: int,
    treat_amount: int,
    product_id: str,
    platform: str,
    original_transaction_id: Optional[str] = None,
    device_fingerprint: Optional[str] = None,
    app_version: Optional[str] = None
) -> PurchaseTransaction:
    """
    Store transaction record for idempotency and audit trail
    
    NOTE: Does NOT commit - caller must commit for atomicity.
    Use db.flush() to check constraint without committing.
    Raises IntegrityError if transaction_id already exists (unique constraint).
    """
    transaction = PurchaseTransaction(
        user_id=user_id,
        transaction_id=transaction_id,
        original_transaction_id=original_transaction_id,
        product_id=product_id,
        treat_amount=treat_amount,
        platform=platform,
        device_fingerprint=device_fingerprint,
        app_version=app_version,
        processed_at=datetime.utcnow()
    )
    db.add(transaction)
    # Flush to check constraint without committing
    # Caller will handle the commit for atomicity
    db.flush()
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
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify purchase directly with RevenueCat API and grant treats
    
    This endpoint:
    - Verifies the purchase with RevenueCat API
    - Checks if transaction exists in RevenueCat customer info
    - Validates that treat amount matches the product ID (security)
    - Prevents duplicate processing (idempotency)
    - Grants treats to the user
    - Records the transaction
    """
    logger = get_logger(__name__)
    
    try:
        # Extract device fingerprint and app version from headers
        device_fingerprint = request.headers.get("Device-Fingerprint")
        app_version = request.headers.get("App-Version")
        
        logger.info(f"Verifying purchase for user {current_user.id}")
        logger.info(f"RevenueCat User ID: {request_data.revenue_cat_user_id}")
        logger.info(f"Transaction ID: {request_data.transaction_id}")
        logger.info(f"Product ID: {request_data.product_id}")
        logger.info(f"Platform: {request_data.platform}")
        if device_fingerprint:
            logger.info(f"Device Fingerprint: {device_fingerprint[:20]}...")  # Log partial for security
        if app_version:
            logger.info(f"App Version: {app_version}")
        
        # Check if this is a StoreKit simulator/sandbox transaction
        is_simulator = request_data.revenue_cat_user_id.startswith("$RCAnonymousID")
        
        # 1. Verify with RevenueCat API with retry mechanism
        # RevenueCat processes transactions asynchronously, so we may need to retry
        max_retries = 3
        retry_delay = 1.0  # Start with 1 second delay
        transaction_found = False
        customer_info = None
        
        for attempt in range(max_retries):
            customer_info = await verify_with_revenuecat_api(
                request_data.revenue_cat_user_id,
                request_data.platform
            )
            
            logger.info(f"RevenueCat API response received successfully (attempt {attempt + 1}/{max_retries})")
            
            # 2. Check if transaction exists in customer_info
            transaction_found = transaction_exists_in_customer_info(
                customer_info, 
                request_data.transaction_id, 
                request_data.product_id
            )
            
            if transaction_found:
                logger.info(f"✅ Transaction found in RevenueCat on attempt {attempt + 1}")
                break
            
            # If not found and not last attempt, wait and retry
            if attempt < max_retries - 1:
                logger.info(
                    f"Transaction not found yet (attempt {attempt + 1}/{max_retries}). "
                    f"Retrying in {retry_delay} seconds..."
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff: 1s, 2s, 4s
        
        if not transaction_found:
            # Log more details about what we received
            # Ensure customer_info is a dict before accessing it
            if isinstance(customer_info, dict):
                subscriber = customer_info.get("subscriber", {})
                non_subscriptions = subscriber.get("non_subscriptions", {}) if isinstance(subscriber, dict) else {}
                other_purchases = subscriber.get("other_purchases", {}) if isinstance(subscriber, dict) else {}
                
                logger.error(f"Transaction not found after {max_retries} attempts. Available products in non_subscriptions: {list(non_subscriptions.keys()) if isinstance(non_subscriptions, dict) else []}")
                logger.error(f"Available products in other_purchases: {list(other_purchases.keys()) if isinstance(other_purchases, dict) else []}")
            else:
                logger.error(f"Transaction not found after {max_retries} attempts. Invalid customer_info type: {type(customer_info)}")
                non_subscriptions = {}
                other_purchases = {}
            
            logger.error(f"Looking for product_id: {request_data.product_id}, transaction_id: {request_data.transaction_id}")
            
            # Development mode: Allow simulator/sandbox purchases to bypass RevenueCat verification
            # This handles cases where RevenueCat hasn't synced yet or simulator transactions
            if is_simulator and RevenueCat.ALLOW_SIMULATOR_BYPASS:
                logger.warning(
                    f"⚠️ DEVELOPMENT MODE: Allowing simulator/sandbox purchase to bypass RevenueCat verification. "
                    f"Transaction ID: {request_data.transaction_id}, Product ID: {request_data.product_id}. "
                    f"Note: Purchase was posted to RevenueCat but hasn't appeared in customer info yet."
                )
                # Skip RevenueCat verification for simulator/sandbox in development mode
                transaction_found = True
            else:
                error_detail = (
                    f"Transaction not found in RevenueCat after {max_retries} attempts. "
                    f"Product ID: {request_data.product_id}, Transaction ID: {request_data.transaction_id}. "
                )
                
                if is_simulator:
                    error_detail += (
                        "Note: StoreKit simulator/sandbox transactions may take a few seconds to sync to RevenueCat. "
                        "Make sure the RevenueCat SDK has processed the purchase on the client side before verifying. "
                        "For development/testing, set REVENUECAT_ALLOW_SIMULATOR_BYPASS=true to bypass verification."
                    )
                else:
                    error_detail += (
                        "This may indicate a timing issue - RevenueCat processes transactions asynchronously. "
                        "Please try again in a few seconds."
                    )
                
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_detail
                )
        
        # 3. Validate treat amount matches product ID
        expected_treats = RevenueCat.PRODUCT_TREAT_MAPPING.get(request_data.product_id)
        if expected_treats is None:
            logger.error(f"Unknown product ID: {request_data.product_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown product ID: {request_data.product_id}"
            )
        
        if request_data.treat_amount != expected_treats:
            logger.error(
                f"Treat amount mismatch for product {request_data.product_id}. "
                f"Expected: {expected_treats}, Received: {request_data.treat_amount}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Treat amount mismatch. Product '{request_data.product_id}' should grant "
                    f"{expected_treats} treats, but received {request_data.treat_amount} treats."
                )
            )
        
        logger.info(f"✅ Treat amount validated: {request_data.treat_amount} treats for product {request_data.product_id}")
        
        # 4. Quick check for duplicate (optimization - database constraint is the real guard)
        # This avoids unnecessary work if transaction already processed
        if transaction_already_processed(db, request_data.transaction_id):
            # Already processed, return current balance
            store_items = get_user_store_items(db, current_user.id)
            logger.info(f"Transaction already processed. Returning current treat balance: {store_items.treats}")
            return VerifyTreatPurchaseResponse(
                success=True,
                treats=store_items.treats,
                message="Transaction already processed"
            )
        
        # 5. Atomic transaction: Store transaction FIRST (database-level idempotency)
        # The unique constraint on transaction_id prevents race conditions
        # If this succeeds, we know the transaction hasn't been processed yet
        try:
            transaction_record = store_transaction(
                db,
                request_data.transaction_id,
                current_user.id,
                request_data.treat_amount,
                request_data.product_id,
                request_data.platform,
                request_data.original_transaction_id,
                device_fingerprint=device_fingerprint,
                app_version=app_version
            )
            
            # 6. Grant treats (only if transaction record was successfully added)
            # Both operations are in the same transaction - atomicity guaranteed
            store_items = grant_treats_to_user(
                db,
                current_user.id,
                request_data.treat_amount
            )
            
            # 7. Commit both operations atomically
            # If commit fails, both changes are rolled back
            db.commit()
            
        except IntegrityError:
            # Transaction already exists (race condition caught at database level)
            db.rollback()
            store_items = get_user_store_items(db, current_user.id)
            logger.info(
                f"Transaction already processed (race condition detected). "
                f"Returning current treat balance: {store_items.treats}"
            )
            return VerifyTreatPurchaseResponse(
                success=True,
                treats=store_items.treats,
                message="Transaction already processed"
            )
        
        # 8. Refresh store_items to ensure we have the absolute latest treat balance
        db.refresh(store_items)
        
        # 9. Log the calculation (we know the amount added, and we have the final balance)
        final_treat_balance = store_items.treats
        logger.info(
            f"✅ Treat purchase complete. "
            f"Added: {request_data.treat_amount} treats. "
            f"Final balance: {final_treat_balance}"
        )
        
        # 10. Return success with full treat balance (existing + purchased)
        return VerifyTreatPurchaseResponse(
            success=True,
            treats=final_treat_balance,
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


