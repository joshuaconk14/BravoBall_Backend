"""
premium_service.py
Premium subscription business logic and service functions
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from models import User, PremiumSubscription, CustomDrill, CompletedSession
from schemas import PremiumStatus, SubscriptionPlan, PremiumFeature

logger = logging.getLogger(__name__)

class PremiumService:
    """Service class for premium subscription management"""
    
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
    
    @staticmethod
    def get_user_subscription(db: Session, user_id: int) -> Optional[PremiumSubscription]:
        """Get or create user's premium subscription"""
        subscription = db.query(PremiumSubscription).filter(
            PremiumSubscription.user_id == user_id
        ).first()
        
        if not subscription:
            # Create default free subscription
            subscription = PremiumSubscription(
                user_id=user_id,
                status="free",
                plan_type="free",
                start_date=datetime.utcnow(),
                is_active=True
            )
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            logger.info(f"Created default free subscription for user {user_id}")
        
        return subscription
    
    @staticmethod
    def get_premium_status(db: Session, user_id: int) -> Dict[str, Any]:
        """Get user's premium status with features"""
        subscription = PremiumService.get_user_subscription(db, user_id)
        
        # Check if subscription is expired
        if subscription.end_date and subscription.end_date < datetime.utcnow():
            subscription.status = "expired"
            subscription.is_active = False
            db.commit()
            logger.info(f"Subscription expired for user {user_id}")
        
        # Determine features based on status
        features = []
        for feature, allowed_statuses in PremiumService.PREMIUM_FEATURES.items():
            if subscription.status in allowed_statuses:
                features.append(feature)
        
        # Format dates for response
        start_date = subscription.start_date.isoformat() + "Z" if subscription.start_date else None
        end_date = subscription.end_date.isoformat() + "Z" if subscription.end_date else None
        trial_end_date = subscription.trial_end_date.isoformat() + "Z" if subscription.trial_end_date else None
        
        return {
            "status": subscription.status,
            "plan": subscription.plan_type,
            "startDate": start_date,
            "endDate": end_date,
            "trialEndDate": trial_end_date,
            "isActive": subscription.is_active,
            "features": features
        }
    
    @staticmethod
    def can_access_feature(db: Session, user_id: int, feature: str) -> Dict[str, Any]:
        """Check if user can access a specific feature"""
        subscription = PremiumService.get_user_subscription(db, user_id)
        
        # Check if feature is accessible
        allowed_statuses = PremiumService.PREMIUM_FEATURES.get(feature, [])
        
        if not allowed_statuses:
            return {
                "canAccess": False,
                "feature": feature,
                "remainingUses": None,
                "limit": "not_available"
            }
        elif subscription.status in allowed_statuses:
            return {
                "canAccess": True,
                "feature": feature,
                "remainingUses": None,
                "limit": "unlimited"
            }
        else:
            # Check specific limits for free users
            if feature == "unlimitedCustomDrills":
                current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                used = db.query(CustomDrill).filter(
                    CustomDrill.user_id == user_id,
                    CustomDrill.created_at >= current_month
                ).count()
                remaining_uses = max(0, PremiumService.FREE_TIER_LIMITS["custom_drills_per_month"] - used)
                can_access = remaining_uses > 0
                limit = f"{PremiumService.FREE_TIER_LIMITS['custom_drills_per_month']} per month"
            elif feature == "unlimitedSessions":
                today = datetime.now().date()
                used = db.query(CompletedSession).filter(
                    CompletedSession.user_id == user_id,
                    func.date(CompletedSession.date) == today
                ).count()
                remaining_uses = max(0, PremiumService.FREE_TIER_LIMITS["sessions_per_day"] - used)
                can_access = remaining_uses > 0
                limit = f"{PremiumService.FREE_TIER_LIMITS['sessions_per_day']} per day"
            else:
                can_access = False
                remaining_uses = 0
                limit = "premium_only"
            
            return {
                "canAccess": can_access,
                "feature": feature,
                "remainingUses": remaining_uses,
                "limit": limit
            }
    

    
    @staticmethod
    def get_usage_stats(db: Session, user_id: int) -> Dict[str, Any]:
        """Get usage statistics for the current user"""
        try:
            # Get current month usage
            current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Get custom drills used this month
            custom_drills_used = db.query(CustomDrill).filter(
                CustomDrill.user_id == user_id,
                CustomDrill.created_at >= current_month
            ).count()
            
            # Get sessions used today
            today = datetime.now().date()
            sessions_used = db.query(CompletedSession).filter(
                CompletedSession.user_id == user_id,
                func.date(CompletedSession.date) == today
            ).count()
            
            # Get subscription status
            subscription = PremiumService.get_user_subscription(db, user_id)
            
            if subscription.status in ["premium", "trial"]:
                # Premium users have unlimited access
                custom_drills_remaining = None
                sessions_remaining = None
            else:
                # Free users have limits
                custom_drills_remaining = max(0, PremiumService.FREE_TIER_LIMITS["custom_drills_per_month"] - custom_drills_used)
                sessions_remaining = max(0, PremiumService.FREE_TIER_LIMITS["sessions_per_day"] - sessions_used)
            
            return {
                "customDrillsRemaining": custom_drills_remaining,
                "sessionsRemaining": sessions_remaining,
                "customDrillsUsed": custom_drills_used,
                "sessionsUsed": sessions_used,
                "isPremium": subscription.status in ["premium", "trial"]
            }
            
        except Exception as e:
            logger.error(f"Error getting usage stats for user {user_id}: {str(e)}")
            return {}
    
    @staticmethod
    def update_subscription(db: Session, user_id: int, status: str, plan_type: str,
                           end_date: Optional[datetime] = None, platform: Optional[str] = None,
                           receipt_data: Optional[str] = None) -> bool:
        """Update user's premium subscription"""
        try:
            subscription = PremiumService.get_user_subscription(db, user_id)
            
            subscription.status = status
            subscription.plan_type = plan_type
            subscription.is_active = status in ["premium", "trial"]
            subscription.end_date = end_date
            subscription.platform = platform
            subscription.receipt_data = receipt_data
            subscription.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Subscription updated for user {user_id}: {status} - {plan_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating subscription for user {user_id}: {str(e)}")
            db.rollback()
            return False
    
    @staticmethod
    def start_trial(db: Session, user_id: int, trial_days: int = 7) -> bool:
        """Start a trial period for a user"""
        try:
            subscription = PremiumService.get_user_subscription(db, user_id)
            
            trial_end = datetime.utcnow() + timedelta(days=trial_days)
            
            subscription.status = "trial"
            subscription.plan_type = "trial"
            subscription.trial_end_date = trial_end
            subscription.is_active = True
            subscription.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Trial started for user {user_id}, ends {trial_end}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting trial for user {user_id}: {str(e)}")
            db.rollback()
            return False
    
    @staticmethod
    def check_trial_expiry(db: Session) -> List[int]:
        """Check for expired trials and return list of user IDs"""
        try:
            expired_trials = db.query(PremiumSubscription).filter(
                PremiumSubscription.status == "trial",
                PremiumSubscription.trial_end_date < datetime.utcnow()
            ).all()
            
            user_ids = []
            for trial in expired_trials:
                trial.status = "expired"
                trial.is_active = False
                trial.updated_at = datetime.utcnow()
                user_ids.append(trial.user_id)
            
            if user_ids:
                db.commit()
                logger.info(f"Expired trials processed for {len(user_ids)} users")
            
            return user_ids
            
        except Exception as e:
            logger.error(f"Error checking trial expiry: {str(e)}")
            db.rollback()
            return []
    
    @staticmethod
    def get_subscription_analytics(db: Session) -> Dict[str, Any]:
        """Get analytics data for premium subscriptions"""
        try:
            # Count subscriptions by status
            status_counts = db.query(
                PremiumSubscription.status,
                db.func.count(PremiumSubscription.id)
            ).group_by(PremiumSubscription.status).all()
            
            # Count subscriptions by plan
            plan_counts = db.query(
                PremiumSubscription.plan_type,
                db.func.count(PremiumSubscription.id)
            ).group_by(PremiumSubscription.plan_type).all()
            
            # Count active subscriptions
            active_count = db.query(PremiumSubscription).filter(
                PremiumSubscription.is_active == True
            ).count()
            
            # Count total users
            total_users = db.query(User).count()
            
            return {
                "status_counts": dict(status_counts),
                "plan_counts": dict(plan_counts),
                "active_subscriptions": active_count,
                "total_users": total_users,
                "conversion_rate": (active_count / total_users * 100) if total_users > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription analytics: {str(e)}")
            return {}
