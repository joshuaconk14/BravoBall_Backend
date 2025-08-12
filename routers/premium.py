"""
premium.py
Premium subscription management endpoints for BravoBall
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json
import logging

from db import get_db
from models import User, PremiumSubscription, UsageTracking
from schemas import (
    PremiumStatusResponse, PremiumStatusRequest, ReceiptVerificationRequest,
    ReceiptVerificationResponse, UsageTrackingRequest, FeatureAccessRequest,
    FeatureAccessResponse, PremiumStatus, SubscriptionPlan, PremiumFeature
)
from auth import get_current_user

router = APIRouter(prefix="/api/premium", tags=["Premium"])

logger = logging.getLogger(__name__)

# Premium features configuration
PREMIUM_FEATURES = {
    "noAds": ["premium", "trial"],
    "unlimitedDrills": ["premium", "trial"],
    "unlimitedCustomDrills": ["premium", "trial"],
    "unlimitedSessions": ["premium", "trial"],
    "advancedAnalytics": ["premium", "trial"],
    "basicDrills": ["free", "premium", "trial", "expired"],
    "weeklySummaries": ["free", "premium", "trial"],
    "monthlySummaries": ["free", "premium", "trial"]
}

# Free tier limits
FREE_TIER_LIMITS = {
    "custom_drills_per_month": 3,
    "sessions_per_day": 1
}

@router.get("/status")
async def get_premium_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    device_fingerprint: Optional[str] = Header(None, alias="Device-Fingerprint"),
    app_version: Optional[str] = Header(None, alias="App-Version")
):
    """Get current premium status for a user"""
    try:
        # Get or create premium subscription
        subscription = db.query(PremiumSubscription).filter(
            PremiumSubscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            # Create default free subscription
            subscription = PremiumSubscription(
                user_id=current_user.id,
                status="free",
                plan_type="free",
                start_date=datetime.utcnow(),
                is_active=True
            )
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
        
        # Determine features based on status
        features = []
        for feature, allowed_statuses in PREMIUM_FEATURES.items():
            if subscription.status in allowed_statuses:
                features.append(feature)
        
        # Format dates for response
        start_date = subscription.start_date.isoformat() + "Z" if subscription.start_date else None
        end_date = subscription.end_date.isoformat() + "Z" if subscription.end_date else None
        trial_end_date = subscription.trial_end_date.isoformat() + "Z" if subscription.trial_end_date else None
        
        response_data = {
            "status": subscription.status,
            "plan": subscription.plan_type,
            "startDate": start_date,
            "endDate": end_date,
            "trialEndDate": trial_end_date,
            "isActive": subscription.is_active,
            "features": features
        }
        
        logger.info(f"Premium status retrieved for user {current_user.id}: {subscription.status}")
        
        return PremiumStatusResponse(
            success=True,
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error getting premium status for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get premium status")

@router.post("/validate")
async def validate_premium_status(
    request: PremiumStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    device_fingerprint: Optional[str] = Header(None, alias="Device-Fingerprint"),
    app_version: Optional[str] = Header(None, alias="App-Version")
):
    """Validate premium status with server-side checks"""
    try:
        # Get current subscription
        subscription = db.query(PremiumSubscription).filter(
            PremiumSubscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        # Check if subscription is expired
        if subscription.end_date and subscription.end_date < datetime.utcnow():
            subscription.status = "expired"
            subscription.is_active = False
            db.commit()
        
        # Calculate next validation time (5 minutes from now)
        next_validation = datetime.utcnow() + timedelta(minutes=5)
        
        response_data = {
            "status": subscription.status,
            "lastValidated": datetime.utcnow().isoformat() + "Z",
            "nextValidation": next_validation.isoformat() + "Z"
        }
        
        logger.info(f"Premium status validated for user {current_user.id}: {subscription.status}")
        
        return PremiumStatusResponse(
            success=True,
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error validating premium status for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to validate premium status")

@router.post("/verify-receipt")
async def verify_receipt(
    request: ReceiptVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify in-app purchase receipt"""
    try:
        # This is a placeholder implementation
        # In production, you would integrate with App Store Server API or Google Play Developer API
        
        if request.platform not in ["ios", "android"]:
            raise HTTPException(status_code=400, detail="Invalid platform")
        
        # Mock verification - replace with actual platform API calls
        verified = True  # This should come from platform verification
        subscription_status = "active"
        expires_at = (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z"  # Mock expiry
        
        # Update user's subscription
        subscription = db.query(PremiumSubscription).filter(
            PremiumSubscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            subscription = PremiumSubscription(
                user_id=current_user.id,
                status="premium",
                plan_type="yearly" if "yearly" in request.productId else "monthly",
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=365 if "yearly" in request.productId else 30),
                is_active=True,
                platform=request.platform,
                receipt_data=request.receiptData
            )
            db.add(subscription)
        else:
            subscription.status = "premium"
            subscription.plan_type = "yearly" if "yearly" in request.productId else "monthly"
            subscription.start_date = datetime.utcnow()
            subscription.end_date = datetime.utcnow() + timedelta(days=365 if "yearly" in request.productId else 30)
            subscription.is_active = True
            subscription.platform = request.platform
            subscription.receipt_data = request.receiptData
            subscription.updated_at = datetime.utcnow()
        
        db.commit()
        
        response_data = {
            "verified": verified,
            "subscriptionStatus": subscription_status,
            "expiresAt": expires_at,
            "platform": request.platform
        }
        
        logger.info(f"Receipt verified for user {current_user.id} on {request.platform}")
        
        return ReceiptVerificationResponse(
            success=True,
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error verifying receipt for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to verify receipt")

@router.post("/verify-google-play")
async def verify_google_play(
    request: ReceiptVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify Google Play purchase (alias for verify-receipt)"""
    request.platform = "android"
    return await verify_receipt(request, current_user, db)

@router.post("/verify-app-store")
async def verify_app_store(
    request: ReceiptVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify App Store purchase (alias for verify-receipt)"""
    request.platform = "ios"
    return await verify_receipt(request, current_user, db)

@router.post("/track-usage")
async def track_usage(
    request: UsageTrackingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Track feature usage for analytics and limits"""
    try:
        # Parse usage date
        try:
            usage_date = datetime.fromisoformat(request.usageDate.replace('Z', '+00:00'))
        except ValueError:
            usage_date = datetime.utcnow()
        
        # Create usage tracking record
        usage_record = UsageTracking(
            user_id=current_user.id,
            feature_type=request.featureType,
            usage_date=usage_date,
            metadata=request.metadata
        )
        
        db.add(usage_record)
        db.commit()
        
        logger.info(f"Usage tracked for user {current_user.id}: {request.featureType}")
        
        return {"success": True, "message": "Usage tracked successfully"}
        
    except Exception as e:
        logger.error(f"Error tracking usage for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to track usage")

@router.get("/usage-stats")
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage statistics for the current user"""
    try:
        # Get current month usage
        current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get custom drills used this month
        custom_drills_used = db.query(UsageTracking).filter(
            UsageTracking.user_id == current_user.id,
            UsageTracking.feature_type == "custom_drill",
            UsageTracking.usage_date >= current_month
        ).count()
        
        # Get sessions used today
        today = datetime.utcnow().date()
        sessions_used = db.query(UsageTracking).filter(
            UsageTracking.user_id == current_user.id,
            UsageTracking.feature_type == "session",
            UsageTracking.usage_date >= today
        ).count()
        
        # Get subscription status
        subscription = db.query(PremiumSubscription).filter(
            PremiumSubscription.user_id == current_user.id
        ).first()
        
        if subscription and subscription.status in ["premium", "trial"]:
            # Premium users have unlimited access
            custom_drills_remaining = None
            sessions_remaining = None
        else:
            # Free users have limits
            custom_drills_remaining = max(0, FREE_TIER_LIMITS["custom_drills_per_month"] - custom_drills_used)
            sessions_remaining = max(0, FREE_TIER_LIMITS["sessions_per_day"] - sessions_used)
        
        response_data = {
            "customDrillsRemaining": custom_drills_remaining,
            "sessionsRemaining": sessions_remaining,
            "customDrillsUsed": custom_drills_used,
            "sessionsUsed": sessions_used,
            "isPremium": subscription.status in ["premium", "trial"] if subscription else False
        }
        
        return {"success": True, "data": response_data}
        
    except Exception as e:
        logger.error(f"Error getting usage stats for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get usage stats")

@router.post("/check-feature")
async def check_feature_access(
    request: FeatureAccessRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user can access a specific feature"""
    try:
        # Get subscription status
        subscription = db.query(PremiumSubscription).filter(
            PremiumSubscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            subscription = PremiumSubscription(
                user_id=current_user.id,
                status="free",
                plan_type="free",
                start_date=datetime.utcnow(),
                is_active=True
            )
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
        
        # Check if feature is accessible
        feature = request.feature
        allowed_statuses = PREMIUM_FEATURES.get(feature, [])
        
        if not allowed_statuses:
            can_access = False
            remaining_uses = None
            limit = "not_available"
        elif subscription.status in allowed_statuses:
            can_access = True
            remaining_uses = None
            limit = "unlimited"
        else:
            # Check specific limits for free users
            if feature == "unlimitedCustomDrills":
                current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                used = db.query(UsageTracking).filter(
                    UsageTracking.user_id == current_user.id,
                    UsageTracking.feature_type == "custom_drill",
                    UsageTracking.usage_date >= current_month
                ).count()
                remaining_uses = max(0, FREE_TIER_LIMITS["custom_drills_per_month"] - used)
                can_access = remaining_uses > 0
                limit = f"{FREE_TIER_LIMITS['custom_drills_per_month']} per month"
            elif feature == "unlimitedSessions":
                today = datetime.utcnow().date()
                used = db.query(UsageTracking).filter(
                    UsageTracking.user_id == current_user.id,
                    UsageTracking.feature_type == "session",
                    UsageTracking.usage_date >= today
                ).count()
                remaining_uses = max(0, FREE_TIER_LIMITS["sessions_per_day"] - used)
                can_access = remaining_uses > 0
                limit = f"{FREE_TIER_LIMITS['sessions_per_day']} per day"
            else:
                can_access = False
                remaining_uses = 0
                limit = "premium_only"
        
        response_data = {
            "canAccess": can_access,
            "feature": feature,
            "remainingUses": remaining_uses,
            "limit": limit
        }
        
        return FeatureAccessResponse(
            success=True,
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error checking feature access for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check feature access")

@router.post("/subscribe")
async def subscribe_user(
    plan: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Subscribe user to a premium plan (for testing purposes)"""
    try:
        if plan not in ["monthly", "yearly", "lifetime"]:
            raise HTTPException(status_code=400, detail="Invalid plan")
        
        # Get or create subscription
        subscription = db.query(PremiumSubscription).filter(
            PremiumSubscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            subscription = PremiumSubscription(
                user_id=current_user.id,
                status="premium",
                plan_type=plan,
                start_date=datetime.utcnow(),
                is_active=True
            )
            db.add(subscription)
        else:
            subscription.status = "premium"
            subscription.plan_type = plan
            subscription.start_date = datetime.utcnow()
            subscription.is_active = True
            subscription.updated_at = datetime.utcnow()
        
        # Set end date based on plan
        if plan == "monthly":
            subscription.end_date = datetime.utcnow() + timedelta(days=30)
        elif plan == "yearly":
            subscription.end_date = datetime.utcnow() + timedelta(days=365)
        elif plan == "lifetime":
            subscription.end_date = None
        
        db.commit()
        
        logger.info(f"User {current_user.id} subscribed to {plan} plan")
        
        return {"success": True, "message": f"Successfully subscribed to {plan} plan"}
        
    except Exception as e:
        logger.error(f"Error subscribing user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to subscribe user")

@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel user's premium subscription"""
    try:
        subscription = db.query(PremiumSubscription).filter(
            PremiumSubscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        subscription.status = "expired"
        subscription.is_active = False
        subscription.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"User {current_user.id} cancelled subscription")
        
        return {"success": True, "message": "Subscription cancelled successfully"}
        
    except Exception as e:
        logger.error(f"Error cancelling subscription for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")

@router.get("/subscription-details")
async def get_subscription_details(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed subscription information"""
    try:
        subscription = db.query(PremiumSubscription).filter(
            PremiumSubscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        # Check if trial
        is_trial = subscription.status == "trial"
        
        response_data = {
            "id": subscription.id,
            "status": subscription.status,
            "plan": subscription.plan_type,
            "startDate": subscription.start_date.isoformat() + "Z",
            "endDate": subscription.end_date.isoformat() + "Z" if subscription.end_date else None,
            "trialEndDate": subscription.trial_end_date.isoformat() + "Z" if subscription.trial_end_date else None,
            "isActive": subscription.is_active,
            "isTrial": is_trial,
            "platform": subscription.platform,
            "receiptData": subscription.receipt_data
        }
        
        return {"success": True, "data": response_data}
        
    except Exception as e:
        logger.error(f"Error getting subscription details for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get subscription details")

# Test endpoints for development
@router.post("/test/set-status")
async def test_set_status(
    status: str,
    plan: str = "monthly",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test endpoint to set premium status (development only)"""
    try:
        if status not in ["free", "premium", "trial", "expired"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        subscription = db.query(PremiumSubscription).filter(
            PremiumSubscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            subscription = PremiumSubscription(
                user_id=current_user.id,
                status=status,
                plan_type=plan,
                start_date=datetime.utcnow(),
                is_active=status in ["premium", "trial"]
            )
            db.add(subscription)
        else:
            subscription.status = status
            subscription.plan_type = plan
            subscription.is_active = status in ["premium", "trial"]
            subscription.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"success": True, "message": f"Status set to {status}"}
        
    except Exception as e:
        logger.error(f"Error setting test status for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to set test status")
