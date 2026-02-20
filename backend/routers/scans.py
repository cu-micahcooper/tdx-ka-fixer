# backend/routers/scans.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import ScanJob

router = APIRouter(prefix="/api/scans", tags=["scans"])

# Injected at startup with real TDX+Claude dependencies
def run_scan_job(mode: str, db: Session):
    raise NotImplementedError("run_scan_job must be injected via app lifespan")

class TriggerRequest(BaseModel):
    mode: str = "heuristic"

@router.get("")
def list_scans(db: Session = Depends(get_db)):
    return db.query(ScanJob).order_by(ScanJob.started_at.desc()).limit(50).all()

@router.post("/trigger")
def trigger_scan(req: TriggerRequest, db: Session = Depends(get_db)):
    job = run_scan_job(mode=req.mode, db=db)
    return job
