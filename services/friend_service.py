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
        existing = db.query(Friendship).filter(
            ((Friendship.requester_user_id == requester_id) & (Friendship.addressee_user_id == addressee_id)) |
            ((Friendship.requester_user_id == addressee_id) & (Friendship.addressee_user_id == requester_id))
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
        fr = db.query(Friendship).filter(Friendship.id == friendship_id).first()
        if not fr:
            raise HTTPException(status_code=404, detail="Friendship not found")
        if user_id not in (fr.requester_user_id, fr.addressee_user_id):
            raise HTTPException(status_code=403, detail="Not authorized to remove this friendship")
        db.delete(fr)
        db.commit()
        return {"message": "Friend removed"}

    @staticmethod
    def list_friends(db: Session, user_id: int):
        # Return list of users who are friends with user_id
        rows = db.query(Friendship).filter(
            ((Friendship.requester_user_id == user_id) | (Friendship.addressee_user_id == user_id)) &
            (Friendship.status == "accepted")
        ).all()
        
        friend_ids = [
            fr.addressee_user_id if fr.requester_user_id == user_id else fr.requester_user_id
            for fr in rows
        ]
        if not friend_ids:
            return []

        users = db.query(User).filter(User.id.in_(friend_ids)).all()
        return [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
            }
            for u in users
        ]

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
            }
            for fr in rows
            if fr.requester_user_id in user_map
        ]


    @staticmethod
    def list_leaderboard(db: Session, current_user: User):
        friends = FriendService.list_friends(db, current_user.id)
        ranking = []
        ranking.append({"id": current_user.id, "username": current_user.username, "points": current_user.points, "sessions_completed": SessionService.completed_session_count(db, current_user.id)})
        users = db.query(User).filter(User.id.in_([f["id"] for f in friends])).all()
        if users:
           for user in users:
                ranking.append({"id": user.id, "username": user.username, "points": user.points, "sessions_completed": SessionService.completed_session_count(db, user.id)})
        ranking.sort(key=lambda x: x["points"], reverse=True)
        for idx, entry in enumerate(ranking, start=1):
            entry["rank"] = idx
        return ranking

    @staticmethod
    def get_friend_profile(db: Session, user_id: int, friend_id: int):
        friend = db.query(Friendship).filter(  
            ((Friendship.requester_user_id == user_id) & (Friendship.addressee_user_id == friend_id)) |
            ((Friendship.requester_user_id == friend_id) & (Friendship.addressee_user_id == user_id))
        ).first()
        if not friend or friend.status != "accepted":
            raise HTTPException(status_code=404, detail="Friendship not found")
        fr = db.query(User).filter(User.id == friend_id).first()
        if not fr:
            raise HTTPException(status_code=404, detail="User not found")
        return [ 
            { 
                "friend_id": friend_id,
                "username": fr.username, 
                "sessions_completed": SessionService.completed_session_count(db, user_id),
                "daily_time_trained": fr.daily_training_time,
                "weekly_training_days": fr.weekly_training_days,
            }
        ]
        # TODO: Missing favorite skill and profile picture. Also completed session from SessionService but might be found elsewhere. 