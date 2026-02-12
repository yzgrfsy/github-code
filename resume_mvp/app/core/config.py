from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ResumeBoost MVP"
    app_env: str = "dev"
    app_debug: bool = True
    app_secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = "sqlite:///./resume_mvp.db"
    storage_dir: str = "./app/data"
    dev_otp: str = "123456"


@lru_cache
def get_settings() -> Settings:
    return Settings()

