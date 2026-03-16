from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    redis_url: str = "redis://localhost:6379/0"
    cache_backend: Literal["auto", "redis", "memory"] = "auto"
    goldapi_key: str = ""
    alphavantage_key: str = ""
    cache_ttl_commodity: int = 60
    cache_ttl_index: int = 300
    cache_ttl_sector: int = 180
    enable_scheduler: bool = True


settings = Settings()
