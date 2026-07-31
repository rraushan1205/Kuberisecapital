import os
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"

    # Access token durations (short-lived, for API requests)
    access_token_admin_minutes: int = 15
    access_token_user_minutes: int = 30

    # Inactivity timeouts (session expires after this much inactivity)
    inactivity_timeout_admin_minutes: int = 30
    inactivity_timeout_user_minutes: int = 120  # 2 hours

    # Optional: Absolute maximum session duration regardless of activity
    # Set to None for unlimited (as long as user is active)
    absolute_max_session_admin_hours: int | None = None
    absolute_max_session_user_hours: int | None = None

    # Cookie security settings
    cookie_secure: bool = True
    cookie_samesite: str = "strict"

    # Environment detection
    environment: str = "production"

    admin_email: str = "admin@example.com"
    admin_password: str
    registration_invitation_codes: list[str] = []
    backend_cors_origins: list[str] = []
    strategy_storage_path: Path = Path("./storage/strategies")
    trading_engine_url: str | None = None

    # API base URL for constructing callback URLs
    api_base_url: str = "http://localhost:8000"

    # Frontend URL for OAuth callback redirects back into the app
    frontend_url: str = "http://localhost:3000"

    # Broker API Configuration
    # Fyers broker credentials (get from https://myapi.fyers.in/dashboard)
    fyers_app_id: str | None = None
    fyers_secret_id: str | None = None
    fyers_redirect_uri: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("admin_email")
    @classmethod
    def normalize_admin_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("trading_engine_url", mode="before")
    @classmethod
    def normalize_engine_url(cls, value: str | None) -> str | None:
        return value.strip().rstrip("/") if value and value.strip() else None

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        """Validate JWT secret strength to prevent using default/weak secrets."""
        weak_secrets = [
            "replace-with-a-long-unique-secret",
            "GENERATE_YOUR_SECRET_HERE_MINIMUM_64_CHARS",
            "test-jwt-secret",
            "secret",
            "changeme",
        ]

        if value.lower() in [s.lower() for s in weak_secrets]:
            raise ValueError(
                "CRITICAL SECURITY ERROR: You are using a default JWT secret key. "
                "Generate a strong secret with: openssl rand -base64 64"
            )

        if len(value) < 32:
            raise ValueError(
                f"JWT secret key is too short ({len(value)} chars). "
                "Minimum 32 characters required. Generate with: openssl rand -base64 64"
            )

        return value

    @field_validator("admin_password")
    @classmethod
    def validate_admin_password(cls, value: str) -> str:
        """Validate admin password strength in production."""
        weak_passwords = [
            "ChangeMe123!",
            "GENERATE_YOUR_SECURE_PASSWORD_HERE",
            "admin",
            "password",
            "123456",
        ]

        if value in weak_passwords:
            raise ValueError(
                "CRITICAL SECURITY ERROR: You are using a default admin password. "
                "Generate a strong password with: openssl rand -base64 32"
            )

        if len(value) < 12:
            raise ValueError(
                f"Admin password is too weak ({len(value)} chars). "
                "Minimum 12 characters required."
            )

        return value

    # Cookie secure validator temporarily disabled for development
    # TODO: Re-enable for production deployment
    # @field_validator("cookie_secure")
    # @classmethod
    # def validate_cookie_secure(cls, value: bool, info) -> bool:
    #     """Force secure cookies in production environment."""
    #     environment = info.data.get("environment", "production")
    #     if environment.lower() == "production" and not value:
    #         raise ValueError(
    #             "CRITICAL SECURITY ERROR: COOKIE_SECURE must be True in production. "
    #             "Cookies will be transmitted over insecure HTTP otherwise."
    #         )
    #     return value

    @field_validator("cookie_samesite")
    @classmethod
    def validate_cookie_samesite(cls, value: str) -> str:
        """Validate cookie SameSite setting."""
        valid_values = ["strict", "lax", "none"]
        if value.lower() not in valid_values:
            raise ValueError(
                f"Invalid COOKIE_SAMESITE value: {value}. "
                f"Must be one of: {', '.join(valid_values)}"
            )
        return value.lower()


@lru_cache
def get_settings() -> Settings:
    return Settings()
