import json
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
from supabase import create_client


class Settings(BaseSettings):
    # Core settings
    ENVIRONMENT: str = "production"
    DEFAULT_AREA_CODE: str = "212"

    # Google Sheets
    SHEET_ID: str
    GOOGLE_CREDENTIALS: str
    LEADS_SHEET_NAME: str = "AllLeads"

    # Email
    EMAIL_SENDER: str
    EMAIL_API_KEY: str
    EMAIL_DAILY_REPORT_TO: str

    # SMS
    KIXIE_API_KEY: str
    KIXIE_BASE_URL: str
    KIXIE_BUSINESS_ID: str

    # Infrastructure
    PORT: int = 8000
    PROMETHEUS_PORT: int = 8001
    CELERY_BROKER_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_TLS: bool = True

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Batch processing
    BATCH_CHUNK_SIZE: int = 500
    MAX_RETRIES: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    @lru_cache()
    def supabase_client(self):
        return create_client(self.SUPABASE_URL, self.SUPABASE_KEY)

    @property
    def google_credentials(self):
        return json.loads(self.GOOGLE_CREDENTIALS)


settings = Settings()
