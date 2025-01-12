"""
delete_account.py
Endpoint to delete user account
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import User
from db import get_db
from auth import get_current_user

router = APIRouter()

@router.delete("/delete-account/")
async def delete_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        db.delete(current_user)
        db.commit()

        return {"status": "success", "message": "User account deleted successfully"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred while deleting the user account: {str(e)}")
