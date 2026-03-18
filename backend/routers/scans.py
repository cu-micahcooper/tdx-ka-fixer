# backend/routers/scans.py
import threading
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from models import ScanJob

router = APIRouter(prefix="/api/scans", tags=["scans"])

# Injected at startup with real TDX+Claude dependencies
def run_scan_job(mode: str, db: Session):
    raise NotImplementedError("run_scan_job must be injected via app lifespan")

class TriggerRequest(BaseModel):
    mode: str = "heuristic"

def _fmt(dt) -> str | None:
    return dt.isoformat() + "Z" if dt else None

@router.get("")
def list_scans(db: Session = Depends(get_db)):
    jobs = db.query(ScanJob).order_by(ScanJob.started_at.desc()).limit(50).all()
    return [
        {
            "id": j.id,
            "mode": j.mode,
            "status": j.status,
            "started_at": _fmt(j.started_at),
            "completed_at": _fmt(j.completed_at),
            "articles_total": j.articles_total,
            "articles_scanned": j.articles_scanned,
            "articles_flagged": j.articles_flagged,
            "error": j.error,
        }
        for j in jobs
    ]

@router.post("/trigger")
def trigger_scan(req: TriggerRequest):
    """Start a scan in a background thread and return immediately."""
    def _run():
        with SessionLocal() as db:
            run_scan_job(mode=req.mode, db=db)
    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started", "mode": req.mode}
