when a user purchases treats , we are using revenuecat api webhooks to ensure the purchase verification and transaction, and then verifying in the backend to make sure that the purchase went through so we can grant user treats

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import httpx
import os
from datetime import datetime

# Assuming you have these imports from your existing code
from your_auth import get_current_user, User
from your_database import get_db
from your_models import UserStoreItems, PurchaseTransaction

router = APIRouter()

# Request/Response Models
class VerifyTreatPurchaseRequest(BaseModel):
    product_id: str
    package_identifier: str
    treat_amount: int
    transaction_id: str
    purchase_date: str
    revenue_cat_user_id: str
    platform: str

class VerifyTreatPurchaseResponse(BaseModel):
    success: bool
    treats: int
    message: Optional[str] = None

# RevenueCat API Configuration
REVENUECAT_API_KEY = os.getenv("REVENUECAT_API_KEY", "appl_OIYtlnvDkuuhmFAAWJojwiAgBxi")
REVENUECAT_API_URL = "https://api.revenuecat.com/v1"

# Helper Functions
async def verify_with_revenuecat_api(revenue_cat_user_id: str) -> dict:
    """
    Fetch customer info from RevenueCat API to verify purchase
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{REVENUECAT_API_URL}/subscribers/{revenue_cat_user_id}",
            headers={
                "Authorization": f"Bearer {REVENUECAT_API_KEY}",
                "X-Platform": "ios"  # or "android" based on platform
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
    non_subscription_transactions = customer_info.get("subscriber", {}).get("non_subscriptions", {})
    
    # Look for the product_id in transactions
    for product_key, transactions in non_subscription_transactions.items():
        if product_key == product_id:
            # Check if transaction_id exists in this product's transactions
            for transaction in transactions:
                if transaction.get("id") == transaction_id:
                    return True
    
    return False

async def transaction_already_processed(
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

async def grant_treats_to_user(
    db: Session,
    user_id: int,
    treat_amount: int
):
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
            streak_revivers=0
        )
        db.add(store_items)
    else:
        # Increment existing treats
        store_items.treats += treat_amount
    
    db.commit()
    db.refresh(store_items)
    return store_items

async def store_transaction(
    db: Session,
    transaction_id: str,
    user_id: int,
    treat_amount: int,
    product_id: str,
    platform: str
):
    """
    Store transaction record for idempotency
    """
    transaction = PurchaseTransaction(
        user_id=user_id,
        transaction_id=transaction_id,
        product_id=product_id,
        treat_amount=treat_amount,
        platform=platform,
        processed_at=datetime.utcnow()
    )
    db.add(transaction)
    db.commit()
    return transaction

async def get_user_store_items(db: Session, user_id: int) -> UserStoreItems:
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
            streak_revivers=0
        )
        db.add(store_items)
        db.commit()
        db.refresh(store_items)
    
    return store_items

# Main Endpoint
@router.post("/api/store/verify-treat-purchase", response_model=VerifyTreatPurchaseResponse)
async def verify_treat_purchase(
    request_data: VerifyTreatPurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify purchase directly with RevenueCat API and grant treats
    """
    try:
        # 1. Verify with RevenueCat API
        customer_info = await verify_with_revenuecat_api(request_data.revenue_cat_user_id)
        
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
        if await transaction_already_processed(db, request_data.transaction_id):
            # Already processed, return current balance
            store_items = await get_user_store_items(db, current_user.id)
            return VerifyTreatPurchaseResponse(
                success=True,
                treats=store_items.treats,
                message="Transaction already processed"
            )
        
        # 4. Grant treats
        store_items = await grant_treats_to_user(
            db,
            current_user.id,
            request_data.treat_amount
        )
        
        # 5. Record transaction
        await store_transaction(
            db,
            request_data.transaction_id,
            current_user.id,
            request_data.treat_amount,
            request_data.product_id,
            request_data.platform
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