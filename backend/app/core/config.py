from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "Relay Station Ops"
    app_env: str = "local"
    app_debug: bool = True
    app_secret_key: str = Field(min_length=32)
    app_field_encryption_key: str = Field(min_length=32)
    database_url: str = "postgresql+psycopg://relay_station_ops:relay_station_ops@localhost:5432/relay_station_ops"
    access_token_expire_minutes: int = 1440
    file_storage_dir: str = "storage/uploads"
    shop_monitor_auto_sync_enabled: bool = True
    shop_monitor_sync_interval_seconds: int = 300
    shop_monitor_success_interval_seconds: int = 3600
    shop_monitor_failure_cooldown_seconds: int = 3600
    shop_monitor_max_per_batch: int = 1
    sub2api_revenue_auto_sync_enabled: bool = False
    sub2api_revenue_sync_interval_seconds: int = 600
    sub2api_account_check_auto_enabled: bool = True
    sub2api_account_check_interval_seconds: int = 600
    sub2api_account_check_only_operation: bool = False

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def reject_public_default_secrets(self) -> "Settings":
        if self.app_secret_key == "change-me":
            raise ValueError("APP_SECRET_KEY must not use the public default")
        if self.app_field_encryption_key == "change-me-32-byte-base64-key":
            raise ValueError("APP_FIELD_ENCRYPTION_KEY must not use the public default")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
