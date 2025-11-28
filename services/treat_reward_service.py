"""
treat_reward_service.py
Service for granting treat rewards with idempotency.
Separates treat calculation from treat granting logic.
"""

from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from models import User, UserStoreItems
from services.treat_calculator import TreatCalculator
from config import get_logger

logger = get_logger(__name__)


class TreatRewardService:
    """Service for granting treat rewards with idempotency"""
    
    def __init__(self, db: Session):
        self.db = db
        self.calculator = TreatCalculator()
    
    def grant_session_reward(
        self,
        user: User,
        session_data: Dict,
        is_new_session: bool,  # True if session was just created, False if duplicate
        user_context: Optional[Dict] = None
    ) -> Tuple[int, bool]:
        """
        Grant treats for a completed session with idempotency.
        
        Args:
            user: The user to grant treats to
            session_data: Session data for calculation
            is_new_session: Whether this is a newly created session (False = duplicate)
            user_context: Optional user context (streak, etc.)
        
        Returns:
            Tuple of (treats_awarded, was_already_granted)
        """
        # If session already exists (duplicate), treats were already granted
        if not is_new_session:
            logger.info(f"Duplicate session detected for user {user.id}, skipping treat reward")
            return 0, True
        
        # Calculate treats
        treats_amount = self.calculator.calculate_treats(session_data, user_context)
        
        if treats_amount <= 0:
            logger.info(f"No treats calculated for user {user.id}, session_type: {session_data.get('session_type')}")
            return 0, False
        
        # Grant treats to user via UserStoreItems
        self._increment_user_treats(user.id, treats_amount)
        
        logger.info(
            f"Granted {treats_amount} treats to user {user.id} "
            f"(session_type: {session_data.get('session_type')}, "
            f"streak: {user_context.get('current_streak', 0) if user_context else 0})"
        )
        
        return treats_amount, False
    
    def _increment_user_treats(self, user_id: int, amount: int):
        """Increment user's treat balance using UserStoreItems"""
        # Get or create UserStoreItems for this user
        store_items = self.db.query(UserStoreItems).filter(
            UserStoreItems.user_id == user_id
        ).first()
        
        if not store_items:
            # Create new UserStoreItems if it doesn't exist
            store_items = UserStoreItems(
                user_id=user_id,
                treats=amount,
                streak_freezes=0,
                streak_revivers=0,
                used_freezes=[],
                used_revivers=[]
            )
            self.db.add(store_items)
        else:
            # Increment existing treats
            store_items.treats = (store_items.treats or 0) + amount
        
        self.db.commit()
        self.db.refresh(store_items)

