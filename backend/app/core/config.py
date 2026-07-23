from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 480
    cookie_secure: bool = True
    admin_email: str = "admin@example.com"
    admin_password: str = "ChangeMe123!"
    backend_cors_origins: list[str] = []
    strategy_storage_path: Path = Path("./storage/strategies")
    trading_engine_url: str | None = None
    
    # Broker API Configuration
    # Fyers broker credentials (get from https://myapi.fyers.in/dashboard)
    fyers_app_id: str | None = None
    fyers_secret_id: str | None = None
    fyers_redirect_uri: str | None = None
    
    # API base URL for constructing callback URLs
    api_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("admin_email")
    @classmethod
    def normalize_admin_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("trading_engine_url", mode="before")
    @classmethod
    def normalize_engine_url(cls, value: str | None) -> str | None:
        return value.strip().rstrip("/") if value and value.strip() else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
