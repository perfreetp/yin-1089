from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "医院集团随访中心PSQI管理系统"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    DATABASE_URL: str = "sqlite+aiosqlite:///./psqi_followup.db"
    DATABASE_ECHO: bool = False

    SECRET_KEY: str = "psqi-followup-center-secret-key-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    SCHEDULER_ENABLED: bool = True
    ALERT_CHECK_INTERVAL_MINUTES: int = 30
    QUEUE_GENERATE_HOUR: int = 1
    DAILY_QUEUE_GENERATION_HOUR: int = 1

    DEFAULT_CONTACT_INTERVAL_HOURS: int = 24
    DEFAULT_OVERDUE_HOURS: int = 72
    DEFAULT_UPGRADE_HOURS: int = 120


settings = Settings()
