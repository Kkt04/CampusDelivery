"""Application configuration loaded from environment variables (12-factor style).

Every secret or environment-specific value comes from the environment or a local
`.env` file. Defaults are safe for local development only.
"""
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET_PLACEHOLDER = "dev-only-insecure-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Campus Delivery Management System"
    environment: str = "development"  # development | test | production
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "campus_delivery"

    # Authentication
    secret_key: str = DEV_SECRET_PLACEHOLDER
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    password_reset_token_expire_minutes: int = 15
    bcrypt_rounds: int = 12

    # Business rules
    pickup_code_ttl_minutes: int = 30
    pickup_code_max_attempts: int = 5
    collection_deadline_days: int = 3
    storage_allocation_strategy: str = "suitable_size"
    notification_channels: str = "in_app,console_email"
    notification_max_attempts: int = 3

    # SMTP email configuration
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "noreply@campus.example.edu"
    smtp_use_tls: bool = True

    # Abuse protection
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300
    trusted_proxies: str = "127.0.0.1,::1"

    cors_origins: str = "http://localhost:5173"


    @model_validator(mode="after")
    def _refuse_insecure_production(self) -> "Settings":
        if self.environment == "production" and (
            self.secret_key == DEV_SECRET_PLACEHOLDER or len(self.secret_key) < 32
        ):
            raise ValueError("SECRET_KEY must be set to a strong value in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def notification_channel_names(self) -> list[str]:
        return [c.strip() for c in self.notification_channels.split(",") if c.strip()]

    @property
    def trusted_proxy_list(self) -> list[str]:
        return [p.strip() for p in self.trusted_proxies.split(",") if p.strip()]



@lru_cache
def get_settings() -> Settings:
    return Settings()
