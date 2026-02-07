"""
leaderboard_service.py
Business logic for world leaderboard functionality
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_, and_
from models import User
from services.session_service import SessionService
import logging

logger = logging.getLogger(__name__)


class LeaderboardService:
    @staticmethod
    def get_world_leaderboard(db: Session, current_user: User):
        """
        Get world leaderboard with top 50 users and current user's rank.
        
        Ranking logic:
        - Sort by points descending (highest first)
        - If points are equal, sort by sessions_completed descending
        - Assign ranks: rank 1 = highest points, rank 2 = second highest, etc.
        - Multiple users can share the same rank if points are equal
        
        Args:
            db: Database session
            current_user: Current authenticated user
            
        Returns:
            dict with 'top_50' and 'user_rank' keys
        """
        try:
            # Get all users with their completed session counts
            # Using subquery to efficiently get session counts
            from models import CompletedSession
            
            # Subquery to count completed sessions per user
            session_counts = db.query(
                CompletedSession.user_id,
                func.count(CompletedSession.id).label('sessions_completed')
            ).group_by(CompletedSession.user_id).subquery()
            
            # Base query for users with session counts
            base_query = db.query(
                User.id,
                User.username,
                User.points,
                User.avatar_path,
                User.avatar_background_color,
                func.coalesce(session_counts.c.sessions_completed, 0).label('sessions_completed')
            ).outerjoin(
                session_counts, User.id == session_counts.c.user_id
            ).order_by(
                desc(User.points),
                desc(func.coalesce(session_counts.c.sessions_completed, 0))
            )
            
            # OPTIMIZATION: Only fetch top 50 users instead of all users
            top_50_users = base_query.limit(50).all()
            
            # Calculate ranks for top 50 (handling ties correctly)
            # Rank logic: same points AND sessions = same rank, next rank skips tied positions
            # Example: [100pts/10sess, 100pts/10sess, 90pts/15sess] -> ranks [1, 1, 3]
            top_50 = []
            prev_points = None
            prev_sessions = None
            current_rank = 1
            
            for idx, user in enumerate(top_50_users):
                user_points = user.points or 0
                user_sessions = user.sessions_completed or 0
                
                # Determine rank: if different from previous, assign new rank (position-based)
                if prev_points is not None and prev_sessions is not None:
                    # If points or sessions differ, assign new rank (position in list)
                    if user_points != prev_points or user_sessions != prev_sessions:
                        current_rank = idx + 1
                else:
                    # First user always gets rank 1
                    current_rank = 1
                
                top_50.append({
                    "id": user.id,
                    "username": user.username,
                    "points": user_points,
                    "sessions_completed": user_sessions,
                    "rank": current_rank,
                    "avatar_path": user.avatar_path,
                    "avatar_background_color": user.avatar_background_color
                })
                
                # Update previous values for next iteration
                prev_points = user_points
                prev_sessions = user_sessions
            
            # Calculate current user's rank separately (more efficient than loading all users)
            # Get user's points and session count
            user_points = current_user.points or 0
            user_sessions = SessionService.completed_session_count(db, current_user.id)
            
            # Count how many users rank above current user
            # A user ranks above if they have:
            # - More points, OR
            # - Same points but more sessions
            users_above_count = db.query(func.count(User.id)).outerjoin(
                session_counts, User.id == session_counts.c.user_id
            ).filter(
                or_(
                    User.points > user_points,
                    and_(
                        User.points == user_points,
                        func.coalesce(session_counts.c.sessions_completed, 0) > user_sessions
                    )
                )
            ).scalar() or 0
            
            # User's rank is number of users above + 1
            user_rank = users_above_count + 1
            
            # Check if user is already in top_50
            user_rank_entry = None
            for entry in top_50:
                if entry["id"] == current_user.id:
                    user_rank_entry = entry
                    break
            
            # If user not in top 50, create their rank entry
            if not user_rank_entry:
                user_rank_entry = {
                    "id": current_user.id,
                    "username": current_user.username,
                    "points": user_points,
                    "sessions_completed": user_sessions,
                    "rank": user_rank,
                    "avatar_path": current_user.avatar_path,
                    "avatar_background_color": current_user.avatar_background_color
                }
            
            logger.info(f"World leaderboard retrieved: top_50={len(top_50)}, user_rank={user_rank_entry['rank']}")
            
            return {
                "top_50": top_50,
                "user_rank": user_rank_entry
            }
            
        except Exception as e:
            logger.error(f"Error retrieving world leaderboard: {str(e)}", exc_info=True)
            raise
