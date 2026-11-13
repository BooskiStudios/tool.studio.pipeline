"""Application settings, read from environment variables (prefix ``BOOSKI_``) or a ``.env`` file."""

from datetime import timedelta
from enum import StrEnum
from functools import lru_cache

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BOOSKI_", env_file=".env", extra="ignore")

    environment: Environment = Environment.DEVELOPMENT

    database_url: PostgresDsn = Field(
        default=PostgresDsn("postgresql+psycopg://booski@127.0.0.1:5432/booski"),
        description="SQLAlchemy URL. Must use the psycopg (v3) driver: postgresql+psycopg://…",
    )
    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)

    log_level: str = "INFO"

    # --- Sessions -------------------------------------------------------------------------------
    session_idle_minutes: int = Field(
        default=12 * 60, ge=5, description="Sign out after this much inactivity."
    )
    session_absolute_days: int = Field(default=30, ge=1, le=90, description="Maximum session lifetime.")
    session_touch_minutes: int = Field(
        default=5, ge=1, description="How often activity extends a session (limits database writes)."
    )

    # --- Sign-in protection ---------------------------------------------------------------------
    login_window_minutes: int = Field(default=15, ge=1)
    login_max_failures_per_email: int = Field(default=5, ge=1)
    login_max_failures_per_ip: int = Field(default=20, ge=1)

    # --- Invitations ----------------------------------------------------------------------------
    invitation_ttl_hours: int = Field(default=72, ge=1, le=24 * 30)

    # --- Browser requests -----------------------------------------------------------------------
    allowed_origins: list[str] = Field(
        default=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ],
        description="Origins allowed to make state-changing browser requests (JSON list in env).",
    )

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION

    @property
    def sqlalchemy_url(self) -> str:
        return str(self.database_url)

    @property
    def session_idle(self) -> timedelta:
        return timedelta(minutes=self.session_idle_minutes)

    @property
    def session_absolute(self) -> timedelta:
        return timedelta(days=self.session_absolute_days)

    @property
    def session_touch(self) -> timedelta:
        return timedelta(minutes=self.session_touch_minutes)

    @property
    def login_window(self) -> timedelta:
        return timedelta(minutes=self.login_window_minutes)

    @property
    def invitation_ttl(self) -> timedelta:
        return timedelta(hours=self.invitation_ttl_hours)


@lru_cache
def get_settings() -> Settings:
    """Process-wide settings. Tests build their own ``Settings`` instead of using this cache."""
    return Settings()
