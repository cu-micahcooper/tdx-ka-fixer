# backend/tests/test_router_articles.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from models import Base, Article
from main import app
from database import get_db

@pytest.fixture
def client_with_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    def override_db():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[get_db] = override_db
    with Session(engine) as s:
        s.add(Article(tdx_id=1, title="Test Article", body="Body text",
                      category_id=1, category_name="General",
                      heuristic_score=7.0, status="active"))
        s.commit()
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_list_articles(client_with_db):
    response = client_with_db.get("/api/articles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Article"

def test_get_article(client_with_db):
    response = client_with_db.get("/api/articles/1")
    assert response.status_code == 200
    assert response.json()["tdx_id"] == 1

def test_get_article_not_found(client_with_db):
    response = client_with_db.get("/api/articles/999")
    assert response.status_code == 404
