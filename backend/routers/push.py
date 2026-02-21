# backend/routers/push.py
from typing import Callable, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import ApprovedChange, Article

router = APIRouter(prefix="/api/approved", tags=["push"])

# Injected at startup with real TDX dependencies
push_service_factory: Optional[Callable] = None


@router.get("")
def list_approved(db: Session = Depends(get_db)):
    """Return all ApprovedChange records with their push status."""
    changes = (
        db.query(ApprovedChange)
        .options(joinedload(ApprovedChange.queue_item))
        .order_by(ApprovedChange.approved_at.desc())
        .all()
    )
    result = []
    for c in changes:
        article = db.get(Article, c.article_id)
        result.append({
            "id": c.id,
            "article_id": c.article_id,
            "article_title": article.title if article else None,
            "tdx_id": article.tdx_id if article else None,
            "push_status": c.push_status,
            "push_error": c.push_error,
            "approved_at": c.approved_at.isoformat() if c.approved_at else None,
            "pushed_at": c.pushed_at.isoformat() if c.pushed_at else None,
        })
    return result


@router.post("/push-all")
def push_all(db: Session = Depends(get_db)):
    svc = push_service_factory(db)
    results = svc.push_all_pending()
    return results


@router.post("/{id}/push")
def push_one(id: int, db: Session = Depends(get_db)):
    svc = push_service_factory(db)
    try:
        svc.push(id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    change = db.get(ApprovedChange, id)
    return change
