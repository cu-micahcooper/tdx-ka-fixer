# backend/routers/queue.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import ReviewQueue
from services.approval import ApprovalService

router = APIRouter(prefix="/api/queue", tags=["queue"])

class ApproveRequest(BaseModel):
    edited_body: str | None = None

class RejectRequest(BaseModel):
    note: str = ""

@router.get("")
def list_queue(status: str = "pending", db: Session = Depends(get_db)):
    return (
        db.query(ReviewQueue)
        .filter(ReviewQueue.status == status)
        .order_by(ReviewQueue.queued_at)
        .all()
    )

@router.post("/{item_id}/approve")
def approve(item_id: int, req: ApproveRequest = ApproveRequest(),
            db: Session = Depends(get_db)):
    svc = ApprovalService(db=db)
    try:
        svc.approve(queue_item_id=item_id, edited_body=req.edited_body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return db.get(ReviewQueue, item_id)

@router.post("/{item_id}/reject")
def reject(item_id: int, req: RejectRequest, db: Session = Depends(get_db)):
    svc = ApprovalService(db=db)
    try:
        svc.reject(queue_item_id=item_id, note=req.note)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return db.get(ReviewQueue, item_id)

@router.post("/{item_id}/skip")
def skip(item_id: int, db: Session = Depends(get_db)):
    svc = ApprovalService(db=db)
    try:
        svc.skip(queue_item_id=item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return db.get(ReviewQueue, item_id)
