"""
premium.py
Premium subscription management endpoints for BravoBall
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json
import logging

from db import get_db
from models import User, PremiumSubscription, CustomDrill, CompletedSession
from schemas import (
    PremiumStatusResponse, PremiumStatusRequest, ReceiptVerificationRequest,
    ReceiptVerificationResponse, FeatureAccessRequest,
    FeatureAccessResponse, PremiumStatus, SubscriptionPlan, PremiumFeature,
    PurchaseCompletedRequest
)
from auth import get_current_user
from services.rate_limiter import rate_limiter
from services.audit_service import AuditService
from services.receipt_verifier import receipt_verifier
import os

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
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    device_fingerprint: Optional[str] = Header(None, alias="Device-Fingerprint"),
    app_version: Optional[str] = Header(None, alias="App-Version")
):
    """Get current premium status for a user"""
    
    # Enforce device fingerprint presence
    if not device_fingerprint:
        AuditService.log(
            db,
            user_id=current_user.id,
            action="get_premium_status",
            endpoint=str(request.url.path),
            method="GET",
            status="blocked_missing_fingerprint",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            device_fingerprint=device_fingerprint,
            details={"appVersion": app_version},
        )
        raise HTTPException(status_code=400, detail="Device fingerprint required")

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
        
        return PremiumStatusResponse(
            success=True,
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error getting premium status for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get premium status")

@router.post("/validate")
async def validate_current_subscription(
    request: Request,
    body: PremiumStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    device_fingerprint: Optional[str] = Header(None, alias="Device-Fingerprint"),
    app_version: Optional[str] = Header(None, alias="App-Version")
):
    """Validate premium status with server-side checks"""
    """Periodically checks, NOT for receipt validating"""
    
    if not device_fingerprint:
        AuditService.log(
            db,
            user_id=current_user.id,
            action="premium_validate",
            endpoint=str(request.url.path),
            method="POST",
            status="blocked_missing_fingerprint",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            device_fingerprint=device_fingerprint,
            details={"appVersion": app_version},
        )
        raise HTTPException(status_code=400, detail="Device fingerprint required")

    # Rate limit: 5/min per user for validation
    if not rate_limiter.allow(current_user.id, "/api/premium/validate", limit=5, window_seconds=60):
        AuditService.log(
            db,
            user_id=current_user.id,
            action="premium_validate",
            endpoint=str(request.url.path),
            method="POST",
            status="rate_limited",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            device_fingerprint=device_fingerprint,
        )
        raise HTTPException(status_code=429, detail="Too many validation requests")

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
        
        AuditService.log(
            db,
            user_id=current_user.id,
            action="premium_validate",
            endpoint=str(request.url.path),
            method="POST",
            status="success",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            device_fingerprint=device_fingerprint,
            details={"status": subscription.status},
        )
        
        return PremiumStatusResponse(
            success=True,
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error validating premium status for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to validate premium status")



@router.post("/validate-purchase")
async def validate_purchase_and_subscribe(
    request: Request,
    body: ReceiptVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    device_fingerprint: Optional[str] = Header(None, alias="Device-Fingerprint"),
    app_version: Optional[str] = Header(None, alias="App-Version")
):
    """Unified endpoint to validate premium purchases and create/update subscriptions"""
    
    # Enforce device fingerprint presence
    if not device_fingerprint:
        AuditService.log(
            db,
            user_id=current_user.id,
            action="validate_purchase",
            endpoint=str(request.url.path),
            method="POST",
            status="blocked_missing_fingerprint",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            device_fingerprint=device_fingerprint,
            details={"platform": body.platform, "appVersion": app_version},
        )
        raise HTTPException(status_code=400, detail="Device fingerprint required")

    # Rate limit
    if not rate_limiter.allow(current_user.id, "/api/premium/validate-purchase", limit=5, window_seconds=60):
        AuditService.log(
            db,
            user_id=current_user.id,
            action="validate_purchase",
            endpoint=str(request.url.path),
            method="POST",
            status="rate_limited",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            device_fingerprint=device_fingerprint,
        )
        raise HTTPException(status_code=429, detail="Too many receipt verifications")

    # Validate platform
    if body.platform not in ["ios", "android"]:
        raise HTTPException(status_code=400, detail="Invalid platform. Must be 'ios' or 'android'")

    try:
        # Verify receipt using platform-specific logic
        verified, info = await receipt_verifier.verify(body.platform, body.receiptData, body.productId, body.transactionId)
        if not verified:
            AuditService.log(
                db,
                user_id=current_user.id,
                action="validate_purchase",
                endpoint=str(request.url.path),
                method="POST",
                status="failed",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                device_fingerprint=device_fingerprint,
                details={"platform": body.platform, "error": "Receipt verification failed"},
            )
            raise HTTPException(status_code=400, detail="Receipt verification failed")

        # Determine plan type and duration
        plan_type = "yearly" if "yearly" in body.productId else "monthly"
        duration_days = 365 if plan_type == "yearly" else 30
        
        # Get or create subscription
        subscription = db.query(PremiumSubscription).filter(
            PremiumSubscription.user_id == current_user.id
        ).first()

        if not subscription:
            # Create new subscription
            subscription = PremiumSubscription(
                user_id=current_user.id,
                status="premium",
                plan_type=plan_type,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=duration_days),
                is_active=True,
                platform=body.platform,
                receipt_data=body.receiptData
            )
            db.add(subscription)
            logger.info(f"Created new premium subscription for user {current_user.id}: {plan_type}")
        else:
            # Update existing subscription
            subscription.status = "premium"
            subscription.plan_type = plan_type
            subscription.start_date = datetime.utcnow()
            subscription.end_date = datetime.utcnow() + timedelta(days=duration_days)
            subscription.is_active = True
            subscription.platform = body.platform
            subscription.receipt_data = body.receiptData
            subscription.updated_at = datetime.utcnow()
            logger.info(f"Updated subscription for user {current_user.id} to {plan_type}")

        # Commit the transaction
        db.commit()

        # Determine available features based on subscription
        features = []
        for feature, allowed_statuses in PREMIUM_FEATURES.items():
            if subscription.status in allowed_statuses:
                features.append(feature)

        # Prepare response data
        response_data = {
            "isValid": True,
            "verified": True,
            "subscriptionStatus": "active",
            "planType": subscription.plan_type,
            "platform": body.platform,
            "startDate": subscription.start_date.isoformat() + "Z",
            "expiresAt": subscription.end_date.isoformat() + "Z" if subscription.end_date else None,
            "features": features,
            "message": f"Successfully subscribed to {plan_type} plan"
        }

        # Log successful purchase
        AuditService.log(
            db,
            user_id=current_user.id,
            action="validate_purchase",
            endpoint=str(request.url.path),
            method="POST",
            status="success",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            device_fingerprint=device_fingerprint,
            details={
                "platform": body.platform, 
                "planType": subscription.plan_type,
                "durationDays": duration_days,
                "features": features
            },
        )

        return ReceiptVerificationResponse(success=True, data=response_data)

    except HTTPException:
        # Re-raise HTTP exceptions (like 400, 429)
        raise
    except Exception as e:
        # Rollback on any other errors
        db.rollback()
        logger.error(f"Error during purchase validation for user {current_user.id}: {str(e)}")
        
        # Log the error
        AuditService.log(
            db,
            user_id=current_user.id,
            action="validate_purchase",
            endpoint=str(request.url.path),
            method="POST",
            status="error",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            device_fingerprint=device_fingerprint,
            details={"platform": body.platform, "error": str(e)},
        )
        
        raise HTTPException(status_code=500, detail="Failed to process purchase validation")





@router.get("/usage-stats")
async def get_usage_stats(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    device_fingerprint: Optional[str] = Header(None, alias="Device-Fingerprint"),
    app_version: Optional[str] = Header(None, alias="App-Version")
):
    """Get usage statistics for the current user"""
    
    # Enforce device fingerprint presence
    if not device_fingerprint:
        AuditService.log(
            db,
            user_id=current_user.id,
            action="get_usage_stats",
            endpoint=str(request.url.path),
            method="GET",
            status="blocked_missing_fingerprint",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            device_fingerprint=device_fingerprint,
            details={"appVersion": app_version},
        )
        raise HTTPException(status_code=400, detail="Device fingerprint required")

    try:
        # Get current month usage
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get custom drills used this month
        custom_drills_used = db.query(CustomDrill).filter(
            CustomDrill.user_id == current_user.id,
            CustomDrill.created_at >= current_month
        ).count()
        
        # Get sessions used today
        today = datetime.now().date()
        sessions_used = db.query(CompletedSession).filter(
            CompletedSession.user_id == current_user.id,
            func.date(CompletedSession.date) == today
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
    request: Request,
    body: FeatureAccessRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    app_version: Optional[str] = Header(None, alias="App-Version")
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
        feature = body.feature
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
                current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                print(f"🔍 DEBUG: === Checking custom drills for user {current_user.id} ===")
                print(f"🔍 DEBUG: Feature requested: {feature}")
                print(f"🔍 DEBUG: Current month start: {current_month}")
                print(f"🔍 DEBUG: Current local time: {datetime.now()}")
                print(f"🔍 DEBUG: Current local date: {datetime.now().date()}")
                
                # Get all custom drills for this user to see what we're working with
                all_drills = db.query(CustomDrill).filter(CustomDrill.user_id == current_user.id).all()
                print(f"🔍 DEBUG: Total custom drills for user {current_user.id}: {len(all_drills)}")
                for drill in all_drills:
                    print(f"  🔍 DEBUG: Drill '{drill.title}' created at: {drill.created_at}")
                
                # Now check monthly limit
                used = db.query(CustomDrill).filter(
                    CustomDrill.user_id == current_user.id,
                    CustomDrill.created_at >= current_month
                ).count()
                print(f"🔍 DEBUG: Drills created this month (>= {current_month}): {used}")
                
                remaining_uses = max(0, FREE_TIER_LIMITS["custom_drills_per_month"] - used)
                can_access = remaining_uses > 0
                limit = f"{FREE_TIER_LIMITS['custom_drills_per_month']} per month"
                print(f"🔍 DEBUG: Remaining uses: {remaining_uses}, Can access: {can_access}")
                print(f"🔍 DEBUG: === End custom drills check ===\n")
            elif feature == "unlimitedSessions":
                today = datetime.now().date()
                print(f"🔍 DEBUG: === Checking sessions for user {current_user.id} ===")
                print(f"🔍 DEBUG: Feature requested: {feature}")
                print(f"🔍 DEBUG: Today's date: {today}")
                print(f"🔍 DEBUG: Current local time: {datetime.now()}")
                
                # Get all sessions for this user to see what we're working with
                all_sessions = db.query(CompletedSession).filter(CompletedSession.user_id == current_user.id).all()
                print(f"🔍 DEBUG: Total sessions for user {current_user.id}: {len(all_sessions)}")
                for session in all_sessions:
                    print(f"  🔍 DEBUG: Session on {session.date} (type: {session.session_type})")
                
                # Now check daily limit
                used = db.query(CompletedSession).filter(
                    CompletedSession.user_id == current_user.id,
                    func.date(CompletedSession.date) == today
                ).count()
                print(f"🔍 DEBUG: Sessions completed today ({today}): {used}")
                
                remaining_uses = max(0, FREE_TIER_LIMITS["sessions_per_day"] - used)
                can_access = remaining_uses > 0
                limit = f"{FREE_TIER_LIMITS['sessions_per_day']} per day"
                print(f"🔍 DEBUG: Remaining uses: {remaining_uses}, Can access: {can_access}")
                print(f"🔍 DEBUG: === End sessions check ===\n")
            else:
                can_access = False
                remaining_uses = 0
                limit = "premium_only"
        
        print(f"🔍 DEBUG: Final result: canAccess={can_access}, remainingUses={remaining_uses}, limit={limit}")
        print(f"🔍 DEBUG: === End feature access check ===\n")
        
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



@router.post("/cancel")
async def cancel_subscription(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    device_fingerprint: Optional[str] = Header(None, alias="Device-Fingerprint"),
    app_version: Optional[str] = Header(None, alias="App-Version")
):
    """Cancel user's premium subscription"""
    
    # Enforce device fingerprint presence
    if not device_fingerprint:
        AuditService.log(
            db,
            user_id=current_user.id,
            action="cancel_subscription",
            endpoint=str(request.url.path),
            method="POST",
            status="blocked_missing_fingerprint",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            device_fingerprint=device_fingerprint,
            details={"appVersion": app_version},
        )
        raise HTTPException(status_code=400, detail="Device fingerprint required")

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
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    device_fingerprint: Optional[str] = Header(None, alias="Device-Fingerprint"),
    app_version: Optional[str] = Header(None, alias="App-Version")
):
    """Get detailed subscription information"""
    
    # Enforce device fingerprint presence
    if not device_fingerprint:
        AuditService.log(
            db,
            user_id=current_user.id,
            action="get_subscription_details",
            endpoint=str(request.url.path),
            method="GET",
            status="blocked_missing_fingerprint",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            device_fingerprint=device_fingerprint,
            details={"appVersion": app_version},
        )
        raise HTTPException(status_code=400, detail="Device fingerprint required")

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
    request: Request,
    status: str,
    plan: str = "monthly",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    device_fingerprint: Optional[str] = Header(None, alias="Device-Fingerprint"),
    app_version: Optional[str] = Header(None, alias="App-Version")
):
    """Test endpoint to set premium status (development only)"""
    
    # Enforce device fingerprint presence
    if not device_fingerprint:
        AuditService.log(
            db,
            user_id=current_user.id,
            action="test_set_status",
            endpoint=str(request.url.path),
            method="POST",
            status="blocked_missing_fingerprint",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            device_fingerprint=device_fingerprint,
            details={"appVersion": app_version},
        )
        raise HTTPException(status_code=400, detail="Device fingerprint required")

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
