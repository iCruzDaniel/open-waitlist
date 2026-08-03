from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- Database ---
    database_type: Literal["sqlite", "postgres"] = "sqlite"
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/waitlist.db",
        description="SQLAlchemy async database URL",
    )

    # --- Auth ---
    api_key: str = Field(default="changeme-api-key")
    jwt_secret: str = Field(default="changeme-jwt-secret", min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 h

    # --- Admin ---
    enable_admin_panel: bool = False
    admin_email: str = "admin@example.com"
    admin_password: str = Field(default="changeme-admin-password", min_length=8)

    # --- Docs ---
    enable_docs: bool = False

    # --- Rate limiting ---
    rate_limit_entries: str = "10/minute"
    rate_limit_login: str = "5/minute"

    # --- Notifications ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@example.com"
    notify_email_to: str = "admin@example.com"
    webhook_url: str = ""

    # --- Logging ---
    log_level: str = "INFO"
    log_sensitive_redact: bool = True

    # --- Export CSV ---
    export_dir: str = "data/exports"
    export_ttl_minutes: int = 60

    # --- Ports (host bind) ---
    api_port: int = 8000
    db_port: int = 5432

    # --- Security ---
    cors_origins: str = "*"  # comma-separated; set to your domain in production
    max_request_body_size: int = 1_048_576  # 1 MB
    content_security_policy: str = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
