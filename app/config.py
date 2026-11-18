from typing import Literal

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


class Settings(BaseSettings):
    bot_token: SecretStr | None = None
    telegram_admin_ids: str = ""
    github_token: SecretStr | None = None
    database_url: SecretStr = SecretStr("sqlite+aiosqlite:///./nabd.db")
    migration_database_url: SecretStr | None = None
    port: int = Field(default=8080, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

    @field_validator("telegram_admin_ids")
    @classmethod
    def validate_admin_ids(cls, raw: str) -> str:
        if raw.strip() and any(
            not part.strip().isascii() or not part.strip().isdecimal() or not 0 < int(part) < 2**63
            for part in raw.split(",")
        ):
            raise ValueError("TELEGRAM_ADMIN_IDS must contain positive numeric Telegram user IDs")
        return raw

    @property
    def admin_ids_list(self) -> list[int]:
        return [int(part) for part in self.telegram_admin_ids.split(",") if part.strip()]

    def database_dsn(self, *, migration: bool = False) -> URL:
        raw = (self.migration_database_url if migration else None) or self.database_url
        try:
            url = make_url(raw.get_secret_value())
        except Exception:
            raise ValueError("Invalid DATABASE_URL") from None
        if url.drivername in {"postgres", "postgresql", "postgresql+asyncpg", "postgresql+psycopg"}:
            return url.set(drivername="postgresql+psycopg")
        if url.drivername in {"sqlite", "sqlite+aiosqlite"}:
            return url.set(drivername="sqlite+aiosqlite")
        raise ValueError("DATABASE_URL must use PostgreSQL or SQLite")


try:
    settings = Settings()
except ValidationError as error:
    fields = ", ".join(str(item["loc"][0]) for item in error.errors(include_input=False))
    raise SystemExit(f"Invalid settings: {fields}") from None
