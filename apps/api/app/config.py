from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPOSITORY_ROOT / ".env", extra="ignore")
    database_url: str | None = None
    gemini_api_key: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
