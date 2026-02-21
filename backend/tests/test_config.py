# backend/tests/test_config.py
import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

def test_settings_loads_from_env():
    env = {
        "ANTHROPIC_API_KEY": "test-key",
        "TDX_BASE_URL": "https://test.tdx.com/TDWebApi",
        "TDX_APP_ID": "42",
        "TDX_USERNAME": "user@example.com",
        "TDX_PASSWORD": "password",
    }
    with patch.dict(os.environ, env):
        from config import Settings
        s = Settings()
        assert s.anthropic_api_key == "test-key"
        assert s.tdx_app_id == 42
        assert s.tdx_base_url == "https://test.tdx.com/TDWebApi"

def test_settings_missing_required_raises():
    with patch.dict(os.environ, {}, clear=True):
        from config import Settings
        with pytest.raises(ValidationError):
            Settings(_env_file=None)
