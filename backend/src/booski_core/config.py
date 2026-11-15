"""Application settings, read from environment variables (prefix ``BOOSKI_``) or a ``.env`` file."""

from datetime import timedelta
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Self
from urllib.parse import urlsplit

from pydantic import Field, PostgresDsn, SecretStr, field_validator, model_validator
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

    # --- Serving the web app ----------------------------------------------------------------------
    frontend_dist: Path | None = Field(
        default=None,
        description="Folder holding the built frontend (npm run build → dist/). When set, the API also "
        "serves the web app, so browser and API share one origin. Unset in development (Vite serves it).",
    )

    # --- Reverse proxy ----------------------------------------------------------------------------
    trusted_proxies: list[str] = Field(
        default=[],
        description="IP addresses of reverse proxies whose X-Forwarded-For / X-Forwarded-Proto headers are "
        "believed (JSON list in env). Empty: forwarded headers are ignored, so clients can't fake their IP.",
    )

    # --- Backups ----------------------------------------------------------------------------------
    backup_dir: Path = Field(
        default=Path("var/backups"),
        description="Where `booski backup create` writes backups (relative to the working directory). "
        "Keep it outside the repository or in a git-ignored folder; backups contain all studio data.",
    )

    # --- AI providers (PR 3.2) ---------------------------------------------------------------------
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        description="Anthropic API key for the whole server (D32). Unset: no AI provider is configured and "
        "every AI request is blocked. Set it in backend/.env (git-ignored) or the environment; "
        "never commit it.",
    )
    ai_request_timeout_seconds: float = Field(
        default=120, ge=5, le=600, description="Time limit for each attempt of an AI provider request."
    )
    ai_max_retries: int = Field(
        default=2, ge=0, le=5, description="Retries for rate limits, overload, server and connection errors."
    )

    @field_validator("anthropic_api_key", mode="before")
    @classmethod
    def _blank_key_is_no_key(cls, value: object) -> object:
        """An empty value (e.g. an unset variable passed through Docker Compose) means "no key"."""
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def _check_production(self) -> Self:
        """Refuse to start in production with settings that only make sense on a developer's machine."""
        if self.environment is not Environment.PRODUCTION:
            return self
        problems = []
        if not self.allowed_origins:
            problems.append("BOOSKI_ALLOWED_ORIGINS must list the public https:// address of the app")
        insecure = [origin for origin in self.allowed_origins if urlsplit(origin).scheme != "https"]
        if insecure:
            problems.append(f"BOOSKI_ALLOWED_ORIGINS must only list https:// origins (not {insecure})")
        if not self.database_url.hosts()[0].get("password"):
            problems.append("BOOSKI_DATABASE_URL must include a password")
        if problems:
            raise ValueError("Unsafe production configuration: " + "; ".join(problems) + ".")
        return self

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
