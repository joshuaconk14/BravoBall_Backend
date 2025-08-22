"""
audit_service.py
Persist audit events for security monitoring and forensics.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import AuditLog
from datetime import datetime


class AuditService:
    @staticmethod
    def log(
        db: Session,
        *,
        user_id: Optional[int],
        action: str,
        endpoint: str,
        method: str,
        status: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            endpoint=endpoint,
            method=method,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint=device_fingerprint,
            details=details or {},
        )
        db.add(audit)
        db.commit()


