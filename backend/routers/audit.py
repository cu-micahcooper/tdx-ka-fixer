# backend/routers/audit.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import AuditLog
from config import get_settings

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _article_url(tdx_id: int) -> str:
    s = get_settings()
    portal_base = s.tdx_base_url.replace("/TDWebApi", "").rstrip("/")
    return f"{portal_base}/TDClient/{s.tdx_app_id}/Portal/KB/ArticleDet?ID={tdx_id}"


@router.get("")
def list_audit(limit: int = 100, db: Session = Depends(get_db)):
    entries = (
        db.query(AuditLog)
        .order_by(AuditLog.pushed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": e.id,
            "article_id": e.article_id,
            "tdx_id": e.tdx_id,
            "action": e.action,
            "original_body": e.original_body,
            "new_body": e.new_body,
            "pushed_at": e.pushed_at.isoformat() if e.pushed_at else None,
            "tdx_url": _article_url(e.tdx_id),
        }
        for e in entries
    ]
