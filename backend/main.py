# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
from models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TDX KA Fixer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

from routers import articles
app.include_router(articles.router)

from routers import queue
app.include_router(queue.router)

from routers import scans
app.include_router(scans.router)

from routers import audit
app.include_router(audit.router)
