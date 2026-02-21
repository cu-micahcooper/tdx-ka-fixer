# backend/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    anthropic_api_key: str
    tdx_base_url: str
    tdx_app_id: int
    tdx_username: str
    tdx_password: str
    scan_cron: str = "0 2 * * *"
    heuristic_threshold: float = 5.0
    claude_model: str = "claude-sonnet-4-6"

    model_config = SettingsConfigDict(env_file=["../.env", ".env"])

@lru_cache
def get_settings() -> Settings:
    return Settings()
