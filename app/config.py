import json
import os
import logging
import re
from typing import Optional, Dict, Any, Union
from pydantic_settings import BaseSettings
from pydantic import validator, root_validator
from functools import lru_cache
from supabase import create_client

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Core settings
    ENVIRONMENT: str = "production"
    DEFAULT_AREA_CODE: str = "212"

    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS: str
    GOOGLE_SHEETS_TOKEN: str
    GOOGLE_SHEETS_ID: str
    LEADS_SHEET_NAME: str = "AllLeads"

    # Email (Gmail)
    GMAIL_USER: str
    GMAIL_CLIENT_ID: str
    GMAIL_CLIENT_SECRET: str
    GMAIL_REFRESH_TOKEN: str
    EMAIL_PASSWORD: Optional[str] = None  # Previously EMAIL_API_KEY
    REPORT_EMAIL: Optional[str] = None    # Previously EMAIL_DAILY_REPORT_TO

    # SMS
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_PHONE_NUMBER: str

    # Infrastructure
    REDIS_URL: str
    REDIS_PASSWORD: str
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_SSL: bool = True
    PORT: int = 8000
    PROMETHEUS_PORT: int = 8001
    CELERY_BROKER_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: Optional[str] = None  # Previously SUPABASE_KEY

    # Batch processing
    BATCH_CHUNK_SIZE: int = 500
    MAX_RETRIES: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = True

    @validator("GOOGLE_SHEETS_ID")
    def validate_sheet_id(cls, v):
        if not v or len(v) < 10:  # Basic validation for Google Sheet ID format
            raise ValueError("GOOGLE_SHEETS_ID must be a valid Google Sheet ID")
        return v

    @validator("GMAIL_USER")
    def validate_email_sender(cls, v):
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not v or not re.match(email_pattern, v):
            raise ValueError("GMAIL_USER must be a valid email address")
        return v

    @validator("TWILIO_ACCOUNT_SID")
    def validate_kixie_key(cls, v):
        if not v or len(v) < 10:
            raise ValueError("TWILIO_ACCOUNT_SID must be a valid API key")
        return v

    @validator("SUPABASE_URL")
    def validate_supabase_url(cls, v):
        if not v or not v.startswith("https://"):
            raise ValueError("SUPABASE_URL must be a valid HTTPS URL")
        return v

    @root_validator
    def validate_related_settings(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that related settings are consistent."""
        # If email features are enabled, ensure sender is set
        if values.get("EMAIL_PASSWORD") and not values.get("GMAIL_USER"):
            raise ValueError("GMAIL_USER must be set when EMAIL_PASSWORD is provided")

        # If Supabase is enabled, ensure URL is valid
        if values.get("SUPABASE_SERVICE_KEY") and not values.get("SUPABASE_URL"):
            raise ValueError("SUPABASE_URL must be set when SUPABASE_SERVICE_KEY is provided")

        return values

    def validate_optional_settings(self) -> None:
        """Validate optional settings and log warnings for missing values."""
        if not self.EMAIL_PASSWORD:
            logger.warning("EMAIL_PASSWORD is missing—email features will be disabled!")
        if not self.REPORT_EMAIL:
            logger.warning("REPORT_EMAIL is missing—daily reports will be disabled!")
        if not self.SUPABASE_SERVICE_KEY:
            logger.warning("SUPABASE_SERVICE_KEY is missing—Supabase features will be disabled!")

    @property
    @lru_cache()
    def supabase_client(self):
        """Get Supabase client if credentials are available."""
        if not self.SUPABASE_URL or not self.SUPABASE_SERVICE_KEY:
            logger.warning("Supabase service key missing—client not initialized")
            return None
        try:
            return create_client(self.SUPABASE_URL, self.SUPABASE_SERVICE_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            return None

    def log_configuration(self) -> None:
        """Log the current configuration state (excluding sensitive values)."""
        logger.info(f"Environment: {self.ENVIRONMENT}")
        logger.info(f"Port: {self.PORT}")
        logger.info(f"Prometheus Port: {self.PROMETHEUS_PORT}")
        logger.info(f"Batch Chunk Size: {self.BATCH_CHUNK_SIZE}")
        logger.info(f"Max Retries: {self.MAX_RETRIES}")
        logger.info(f"Redis TLS: {self.REDIS_SSL}")
        logger.info(f"Email Features: {'Enabled' if self.EMAIL_PASSWORD else 'Disabled'}")
        logger.info(f"Supabase Features: {'Enabled' if self.SUPABASE_SERVICE_KEY else 'Disabled'}")
        logger.info(f"Google Sheets Integration: {'Enabled' if self.GOOGLE_SHEETS_CREDENTIALS else 'Disabled'}")


# Initialize settings and validate optional values
settings = Settings()
settings.validate_optional_settings()
settings.log_configuration()
