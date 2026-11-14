"""Application settings, read from environment variables (prefix ``BOOSKI_``) or a ``.env`` file."""

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

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION

    @property
    def sqlalchemy_url(self) -> str:
        return str(self.database_url)


@lru_cache
def get_settings() -> Settings:
    """Process-wide settings. Tests build their own ``Settings`` instead of using this cache."""
    return Settings()
