# backend/tests/test_main.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

def test_health_check():
    # Mock settings and scheduler to avoid needing .env in tests
    mock_settings = MagicMock()
    mock_settings.tdx_base_url = "https://test.tdx.com/TDWebApi"
    mock_settings.tdx_app_id = 42
    mock_settings.tdx_beid = "beid"
    mock_settings.tdx_web_services_key = "wskey"
    mock_settings.anthropic_api_key = "fake-key"
    mock_settings.claude_model = "claude-sonnet-4-6"
    mock_settings.heuristic_threshold = 5.0
    mock_settings.scan_cron = "0 2 * * *"

    with patch("main.get_settings", return_value=mock_settings), \
         patch("main.start_scheduler"), \
         patch("main.stop_scheduler"):
        from main import app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
