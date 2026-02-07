"""
leaderboard.py
API endpoints for leaderboard functionality
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from db import get_db
from auth import get_current_user
from models import User, WorldLeaderboardResponse, LeaderboardEntry
from services.leaderboard_service import LeaderboardService
from services.friend_service import FriendService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/leaderboard/world", response_model=WorldLeaderboardResponse)
async def get_world_leaderboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get world leaderboard with top 50 users and current user's rank.
    
    Returns:
        - top_50: List of up to 50 leaderboard entries (sorted by points descending)
        - user_rank: Current user's leaderboard entry (always included)
    
    Ranking:
        - Sort by points descending (highest first)
        - If points are equal, sort by sessions_completed descending
        - Assign ranks: rank 1 = highest points, rank 2 = second highest, etc.
        - Multiple users can share the same rank if points are equal
    """
    try:
        logger.info(f"World leaderboard requested by user {current_user.id} ({current_user.username})")
        
        result = LeaderboardService.get_world_leaderboard(db, current_user)
        
        logger.info(f"World leaderboard retrieved successfully for user {current_user.id}")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving world leaderboard for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve world leaderboard"
        )


@router.get("/api/leaderboard/friends", response_model=List[LeaderboardEntry])
async def get_friends_leaderboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get friends leaderboard showing current user and their friends ranked by points.
    
    Returns:
        List of leaderboard entries including the current user and their friends,
        sorted by points descending, with ranks assigned.
    """
    try:
        logger.info(f"Friends leaderboard requested by user {current_user.id} ({current_user.username})")
        
        result = FriendService.list_leaderboard(db, current_user)
        
        logger.info(f"Friends leaderboard retrieved successfully for user {current_user.id}")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving friends leaderboard for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve friends leaderboard"
        )
