# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

DATABASE_URL = "sqlite:///./ka_fixer.db"

def _set_wal(dbapi_conn, _conn_record):
    dbapi_conn.execute("PRAGMA journal_mode=WAL")

from sqlalchemy import event
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
event.listen(engine, "connect", _set_wal)
SessionLocal = sessionmaker(bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
