"""
friends.py
Routers for friend features: send, accept, decline, remove, list
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db import get_db
from auth import get_current_user
from models import User
from services.friend_service import FriendService

router = APIRouter()


class SendFriendRequest(BaseModel):
    addressee_id: int


@router.post("/api/friends/send")
def send_friend_request(payload: SendFriendRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return FriendService.send_request(db, requester_id=current_user.id, addressee_id=payload.addressee_id)


@router.post("/api/friends/accept/{request_id}")
def accept_friend_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return FriendService.accept_request(db, request_id=request_id, user_id=current_user.id)


@router.post("/api/friends/decline/{request_id}")
def decline_friend_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return FriendService.decline_request(db, request_id=request_id, user_id=current_user.id)


@router.delete("/api/friends/remove/{friendship_id}")
def remove_friend(friendship_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return FriendService.remove_friend(db, friendship_id=friendship_id, user_id=current_user.id)


@router.get("/api/friends")
def list_friends(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return FriendService.list_friends(db, current_user.id)


@router.get("/api/friends/requests")
def list_incoming_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return FriendService.list_requests(db, current_user.id)

@router.get("/api/friends/{friend_id}/profile")
def get_friend_profile(friend_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return FriendService.get_friend_profile(db, current_user.id, friend_id)