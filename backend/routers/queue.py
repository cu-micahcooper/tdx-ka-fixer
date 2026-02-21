# backend/routers/queue.py
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import ReviewQueue
from services.approval import ApprovalService
from config import get_settings

router = APIRouter(prefix="/api/queue", tags=["queue"])

def _article_url(tdx_id: int) -> str:
    s = get_settings()
    # Strip /TDWebApi suffix to get the portal base
    portal_base = s.tdx_base_url.replace("/TDWebApi", "").rstrip("/")
    return f"{portal_base}/TDClient/{s.tdx_app_id}/Portal/KB/ArticleDet?ID={tdx_id}"

class ApproveRequest(BaseModel):
    edited_body: str | None = None

class RejectRequest(BaseModel):
    note: str = ""

def _serialize_item(item: ReviewQueue) -> dict:
    a = item.article
    r = item.analysis
    return {
        "id": item.id,
        "article_id": item.article_id,
        "analysis_id": item.analysis_id,
        "status": item.status,
        "queued_at": item.queued_at.isoformat() if item.queued_at else None,
        "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
        "reviewer_note": item.reviewer_note,
        "article": {
            "id": a.id,
            "tdx_id": a.tdx_id,
            "title": a.title,
            "body": a.body,
            "category_name": a.category_name,
            "modified_at": a.modified_at.isoformat() if a.modified_at else None,
            "tdx_url": _article_url(a.tdx_id),
        } if a else None,
        "analysis": {
            "id": r.id,
            "overall_score": r.overall_score,
            "score_clarity": r.score_clarity,
            "score_completeness": r.score_completeness,
            "score_findability": r.score_findability,
            "score_redundancy": r.score_redundancy,
            "score_accuracy": r.score_accuracy,
            "issue_summary": r.issue_summary,
            "defects": json.loads(r.defects_json) if r.defects_json else [],
            "proposed_body": r.proposed_body,
            "approval_tier": r.approval_tier,
        } if r else None,
    }

@router.get("")
def list_queue(status: str = "pending", db: Session = Depends(get_db)):
    items = (
        db.query(ReviewQueue)
        .options(joinedload(ReviewQueue.article), joinedload(ReviewQueue.analysis))
        .filter(ReviewQueue.status == status)
        .order_by(ReviewQueue.queued_at)
        .all()
    )
    return [_serialize_item(i) for i in items]

def _get_item(item_id: int, db: Session) -> ReviewQueue:
    item = (
        db.query(ReviewQueue)
        .options(joinedload(ReviewQueue.article), joinedload(ReviewQueue.analysis))
        .filter(ReviewQueue.id == item_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return item

@router.post("/{item_id}/approve")
def approve(item_id: int, req: ApproveRequest = ApproveRequest(),
            db: Session = Depends(get_db)):
    from routers.push import push_service_factory
    svc = ApprovalService(db=db)
    try:
        change = svc.approve(queue_item_id=item_id, edited_body=req.edited_body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    # Push the approved body to TDX immediately
    if push_service_factory:
        try:
            push_service_factory(db).push(change.id)
        except Exception as e:
            # Approval is recorded; push can be retried via /api/approved/{id}/push
            import logging
            logging.getLogger(__name__).error("TDX push failed for change %s: %s", change.id, e)
    return _serialize_item(_get_item(item_id, db))

@router.post("/{item_id}/reject")
def reject(item_id: int, req: RejectRequest, db: Session = Depends(get_db)):
    svc = ApprovalService(db=db)
    try:
        svc.reject(queue_item_id=item_id, note=req.note)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _serialize_item(_get_item(item_id, db))

@router.post("/{item_id}/skip")
def skip(item_id: int, db: Session = Depends(get_db)):
    svc = ApprovalService(db=db)
    try:
        svc.skip(queue_item_id=item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _serialize_item(_get_item(item_id, db))
