from sqlalchemy.orm import Session
from models import CompletedSession

class SessionService:
    @staticmethod
    def completed_session_count(db: Session, user_id: int) -> int:
        return db.query(CompletedSession).filter(
            CompletedSession.user_id == user_id
        ).count() or 0
