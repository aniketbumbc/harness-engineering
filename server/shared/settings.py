from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    database_url: str
    mock_store_url: str = "http://localhost:8001"
    refund_approval_threshold: int = 1000
    openai_api_key: str | None = None
    openai_model: str | None = None


settings = Settings()