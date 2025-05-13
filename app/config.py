import json
import os
import logging
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
from supabase import create_client

logger = logging.getLogger(__name__)

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
    EMAIL_API_KEY: Optional[str] = None
    EMAIL_DAILY_REPORT_TO: Optional[str] = None

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
    SUPABASE_KEY: Optional[str] = None

    # Batch processing
    BATCH_CHUNK_SIZE: int = 500
    MAX_RETRIES: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = True

    def validate_optional_settings(self) -> None:
        """Validate optional settings and log warnings for missing values."""
        if not self.EMAIL_API_KEY:
            logger.warning("EMAIL_API_KEY is missing—email features will be disabled!")

        if not self.EMAIL_DAILY_REPORT_TO:
            logger.warning("EMAIL_DAILY_REPORT_TO is missing—daily reports will be disabled!")

        if not self.SUPABASE_KEY:
            logger.warning("SUPABASE_KEY is missing—Supabase features will be disabled!")

    @property
    @lru_cache()
    def supabase_client(self):
        """Get Supabase client if credentials are available."""
        if not self.SUPABASE_URL or not self.SUPABASE_KEY:
            logger.warning("Supabase credentials missing—client not initialized")
            return None
        try:
            return create_client(self.SUPABASE_URL, self.SUPABASE_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            return None

    @property
    def google_credentials(self):
        """Get Google credentials from JSON string."""
        try:
            return json.loads(self.GOOGLE_CREDENTIALS)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GOOGLE_CREDENTIALS: {e}")
            raise


# Initialize settings and validate optional values
settings = Settings()
settings.validate_optional_settings()
