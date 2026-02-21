# backend/routers/push.py
from typing import Callable, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import ApprovedChange

router = APIRouter(prefix="/api/approved", tags=["push"])

# Injected at startup with real TDX dependencies
push_service_factory: Optional[Callable] = None


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
