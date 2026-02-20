# backend/routers/audit.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import AuditLog

router = APIRouter(prefix="/api/audit", tags=["audit"])

@router.get("")
def list_audit(limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(AuditLog)
        .order_by(AuditLog.pushed_at.desc())
        .limit(limit)
        .all()
    )
