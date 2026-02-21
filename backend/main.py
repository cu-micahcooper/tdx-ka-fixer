# backend/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, SessionLocal
from models import Base
from config import get_settings
from services.tdx_client import TDXClient
from services.claude_client import ClaudeAnalyzer
from services.scan_engine import ScanEngine
from services.push_service import PushService
from scheduler import start_scheduler, stop_scheduler
import routers.scans as scans_router
import routers.push as push_router

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app_: FastAPI):
    settings = get_settings()
    tdx = TDXClient(
        base_url=settings.tdx_base_url,
        app_id=settings.tdx_app_id,
        username=settings.tdx_username,
        password=settings.tdx_password,
    )
    analyzer = ClaudeAnalyzer(
        api_key=settings.anthropic_api_key,
        model=settings.claude_model,
    )

    def run_scan(mode: str = "heuristic", db=None):
        with SessionLocal() as session:
            scan_eng = ScanEngine(
                db=session, tdx_client=tdx, analyzer=analyzer,
                heuristic_threshold=settings.heuristic_threshold,
            )
            if mode == "full_batch":
                return scan_eng.run_full_batch_scan()
            return scan_eng.run_heuristic_scan()

    scans_router.run_scan_job = run_scan
    push_router.push_service_factory = lambda db: PushService(db=db, tdx_client=tdx)
    start_scheduler(settings.scan_cron, lambda: run_scan("heuristic"))
    yield
    stop_scheduler()


app = FastAPI(title="TDX KA Fixer", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import articles, queue, scans, audit, stats
app.include_router(articles.router)
app.include_router(queue.router)
app.include_router(scans.router)
app.include_router(audit.router)
app.include_router(push_router.router)
app.include_router(stats.router)


@app.get("/health")
def health():
    return {"status": "ok"}
