"""Application settings, read once from the environment.

Every tunable the SRS leaves configurable lives here, including the
Appendix C values resolved in PLAN.md section 7. Nothing else in the
codebase should read os.environ directly.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---------------------------------------------------
    app_name: str = "ClauseGuard"
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = "dev-only-insecure-change-me"
    # Kept as a string, not list[str]: pydantic-settings JSON-decodes complex
    # types straight from the environment, before any validator runs, so a
    # comma-separated CORS_ORIGINS would fail to parse. Split in the property.
    cors_origins: str = "http://localhost:5173"

    # --- Database ------------------------------------------------------
    postgres_user: str = "clauseguard"
    postgres_password: str = "clauseguard"
    postgres_db: str = "clauseguard"
    postgres_host: str = "localhost"
    # 5433 is the host-published port (see docker-compose.yml); inside the
    # compose network DATABASE_URL overrides this with db:5432.
    postgres_port: int = 5433
    database_url: str | None = None

    # --- Limits (SRS Appendix C / PLAN.md 7) ---------------------------
    # TBD-1: 10 MB cap on uploads.
    max_upload_mb: int = 10
    # TBD-2: global confidence floor; per-class thresholds come from the model card.
    min_confidence_threshold: float = 0.45
    # TBD-4: bounded concurrency, requests beyond this queue rather than drop.
    max_concurrent_analyses: int = 5

    # --- Versions stamped onto every report (SRS 5.5) ------------------
    active_rubric_version: str = "1.0"
    active_model_version: str = "not-trained-yet"

    # --- Storage -------------------------------------------------------
    storage_dir: str = "storage"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        """DATABASE_URL wins when set; otherwise assemble from the parts."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Cached so the environment is parsed once per process."""
    return Settings()
