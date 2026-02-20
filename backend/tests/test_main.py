# backend/tests/test_main.py
import pytest
from fastapi.testclient import TestClient

def test_health_check():
    from main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
