"""
friend_service.py
Business logic for friend requests and relationships
"""
from sqlalchemy.orm import Session
from models import Friendship, User
from datetime import datetime
from fastapi import HTTPException
from services.session_service import SessionService


class FriendService:
    @staticmethod
    def send_request(db: Session, requester_id: int, addressee_id: int) -> Friendship:
        if requester_id == addressee_id:
            raise HTTPException(status_code=400, detail="Cannot send friend request to yourself")

        # Check users exist
        requester = db.query(User).filter(User.id == requester_id).first()
        addressee = db.query(User).filter(User.id == addressee_id).first()
        if not requester or not addressee:
            raise HTTPException(status_code=404, detail="User not found")

        # Check for existing friendship (either direction)
        # Only check for active friendships (pending or accepted), ignore removed ones
        existing = db.query(Friendship).filter(
            ((Friendship.requester_user_id == requester_id) & (Friendship.addressee_user_id == addressee_id)) |
            ((Friendship.requester_user_id == addressee_id) & (Friendship.addressee_user_id == requester_id)),
            Friendship.status.in_(["pending", "accepted"])  # Only check active friendships
        ).first()

        if existing:
            if existing.status == "pending":
                raise HTTPException(status_code=400, detail="Friend request already pending")
            if existing.status == "accepted":
                raise HTTPException(status_code=400, detail="Users are already friends")
       
        friendship = Friendship(
            requester_user_id=requester_id,
            addressee_user_id=addressee_id,
            status="pending",
            created_at=datetime.utcnow()
        )
        db.add(friendship)
        db.commit()
        db.refresh(friendship)
        return friendship

    @staticmethod
    def accept_request(db: Session, request_id: int, user_id: int) -> Friendship:
        fr = db.query(Friendship).filter(Friendship.id == request_id).first()
        if not fr:
            raise HTTPException(status_code=404, detail="Friend request not found")
        if fr.addressee_user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to accept this request")
        fr.status = "accepted"
        fr.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(fr)
        return fr

    @staticmethod
    def decline_request(db: Session, request_id: int, user_id: int) -> Friendship:
        fr = db.query(Friendship).filter(Friendship.id == request_id).first()
        if not fr:
            raise HTTPException(status_code=404, detail="Friend request not found")
        if fr.addressee_user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to decline this request")
        db.delete(fr)
        db.commit()
        return {"message": "Friend request declined"}

    @staticmethod
    def remove_friend(db: Session, friendship_id: int, user_id: int):
        # Find the friendship - must be accepted and user must be part of it
        friendship = db.query(Friendship).filter(
            Friendship.id == friendship_id,
            ((Friendship.requester_user_id == user_id) | (Friendship.addressee_user_id == user_id)),
            Friendship.status == "accepted"
        ).first()
        
        if not friendship:
            raise HTTPException(
                status_code=404,
                detail="Friendship not found or you don't have permission to remove it"
            )
        
        # Soft delete: Update status instead of deleting
        friendship.status = "removed"
        friendship.removed_at = datetime.utcnow()
        friendship.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(friendship)
        
        return {"message": "Friend removed successfully"}

    @staticmethod
    def list_friends(db: Session, user_id: int):
        # Return list of users who are friends with user_id
        # Only return active friendships (status == 'accepted')
        friendships = db.query(Friendship).filter(
            ((Friendship.requester_user_id == user_id) | (Friendship.addressee_user_id == user_id)) &
            (Friendship.status == "accepted")
        ).all()
        
        if not friendships:
            return []

        # Build response with friendship_id
        friends_list = []
        for friendship in friendships:
            # Get the friend user (the other user in the friendship)
            friend_user = friendship.addressee if friendship.requester_user_id == user_id else friendship.requester
            
            friends_list.append({
                "id": friend_user.id,
                "friendship_id": friendship.id,  # The friendships.id primary key
                "username": friend_user.username,
                "email": friend_user.email,
                "avatar_path": friend_user.avatar_path,
                "avatar_background_color": friend_user.avatar_background_color,
            })
        
        return friends_list

    @staticmethod
    def list_requests(db: Session, user_id: int):
        # Incoming pending requests
        rows = db.query(Friendship).filter(
            Friendship.addressee_user_id == user_id,
            Friendship.status == "pending"
        ).all()

        requester_ids = [fr.requester_user_id for fr in rows]
        if not requester_ids:
            return []

        users = db.query(User).filter(User.id.in_(requester_ids)).all()
        user_map = {u.id: u for u in users}

        return [
            {
                "request_id": fr.id,
                "requester_id": fr.requester_user_id,
                "username": user_map[fr.requester_user_id].username,
                "email": user_map[fr.requester_user_id].email,
                "avatar_path": user_map[fr.requester_user_id].avatar_path,
                "avatar_background_color": user_map[fr.requester_user_id].avatar_background_color,
            }
            for fr in rows
            if fr.requester_user_id in user_map
        ]


    @staticmethod
    def list_leaderboard(db: Session, current_user: User):
        friends = FriendService.list_friends(db, current_user.id)
        ranking = []
        ranking.append({
            "id": current_user.id,
            "username": current_user.username,
            "points": current_user.points,
            "sessions_completed": SessionService.completed_session_count(db, current_user.id),
            "avatar_path": current_user.avatar_path,
            "avatar_background_color": current_user.avatar_background_color
        })
        users = db.query(User).filter(User.id.in_([f["id"] for f in friends])).all()
        if users:
           for user in users:
                ranking.append({
                    "id": user.id,
                    "username": user.username,
                    "points": user.points,
                    "sessions_completed": SessionService.completed_session_count(db, user.id),
                    "avatar_path": user.avatar_path,
                    "avatar_background_color": user.avatar_background_color
                })
        ranking.sort(key=lambda x: x["points"], reverse=True)
        for idx, entry in enumerate(ranking, start=1):
            entry["rank"] = idx
        return ranking

    @staticmethod
    def get_friend_profile(db: Session, user_id: int, friend_id: int):
        # Only get active friendships (status == 'accepted')
        friendship = db.query(Friendship).filter(  
            ((Friendship.requester_user_id == user_id) & (Friendship.addressee_user_id == friend_id)) |
            ((Friendship.requester_user_id == friend_id) & (Friendship.addressee_user_id == user_id)),
            Friendship.status == "accepted"  # Only active friendships
        ).first()
        if not friendship:
            raise HTTPException(status_code=404, detail="Friendship not found")
        
        friend_user = db.query(User).filter(User.id == friend_id).first()
        if not friend_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get friend's session count
        friend_sessions = SessionService.completed_session_count(db, friend_id)
        
        # Calculate rank from world leaderboard (not friends leaderboard)
        from sqlalchemy import desc, func, or_, and_
        from models import CompletedSession
        
        # Subquery to count completed sessions per user
        session_counts = db.query(
            CompletedSession.user_id,
            func.count(CompletedSession.id).label('sessions_completed')
        ).group_by(CompletedSession.user_id).subquery()
        
        # Get friend's points and sessions
        friend_points = friend_user.points or 0
        
        # Count how many users rank above friend in world leaderboard
        # A user ranks above if they have:
        # - More points, OR
        # - Same points but more sessions
        users_above_count = db.query(func.count(User.id)).outerjoin(
            session_counts, User.id == session_counts.c.user_id
        ).filter(
            or_(
                User.points > friend_points,
                and_(
                    User.points == friend_points,
                    func.coalesce(session_counts.c.sessions_completed, 0) > friend_sessions
                )
            )
        ).scalar() or 0
        
        # Friend's world rank is number of users above + 1
        friend_rank = users_above_count + 1
        
        # Get friend's progress history for streaks and favorite drill
        from models import ProgressHistory
        progress_history = db.query(ProgressHistory).filter(
            ProgressHistory.user_id == friend_id
        ).first()
        
        # Get streaks from progress history
        current_streak = progress_history.current_streak if progress_history else 0
        highest_streak = progress_history.highest_streak if progress_history else 0
        favorite_drill = progress_history.favorite_drill if (progress_history and progress_history.favorite_drill) else ""
        
        # Get last active date (most recent completed session)
        last_session = db.query(CompletedSession).filter(
            CompletedSession.user_id == friend_id
        ).order_by(desc(CompletedSession.date)).first()
        
        last_active = last_session.date if last_session else None
        
        # Get total practice minutes from progress history
        total_practice_minutes = progress_history.total_time_all_sessions if progress_history else 0
        
        return {
            "id": friend_user.id,
            "friendship_id": friendship.id,
            "username": friend_user.username,
            "email": friend_user.email,
            "first_name": friend_user.first_name,
            "last_name": friend_user.last_name,
            "avatar_path": friend_user.avatar_path,
            "avatar_background_color": friend_user.avatar_background_color,
            "points": friend_user.points or 0,
            "sessions_completed": friend_sessions,
            "rank": friend_rank,
            "current_streak": current_streak,
            "highest_streak": highest_streak,
            "favorite_drill": favorite_drill,
            "last_active": last_active.isoformat() if last_active else None,
            "total_practice_minutes": total_practice_minutes
        } 