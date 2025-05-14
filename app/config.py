import json
import os
import logging
import re
from typing import Optional, Dict, Any, Union
from pydantic_settings import BaseSettings
from pydantic import validator, model_validator
from functools import lru_cache
from supabase import create_client

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Core settings
    ENVIRONMENT: str = "production"
    DEFAULT_AREA_CODE: str = "212"

    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS: Optional[str] = None
    GOOGLE_SHEETS_TOKEN: Optional[str] = None
    GOOGLE_SHEETS_ID: Optional[str] = None
    LEADS_SHEET_NAME: str = "AllLeads"

    # Email (Gmail)
    GMAIL_USER: Optional[str] = None
    GMAIL_CLIENT_ID: Optional[str] = None
    GMAIL_CLIENT_SECRET: Optional[str] = None
    GMAIL_REFRESH_TOKEN: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    REPORT_EMAIL: Optional[str] = None

    # SMS (Kixie)
    KIXIE_API_KEY: Optional[str] = None
    KIXIE_BASE_URL: Optional[str] = None

    # Core Infrastructure
    PORT: int = 8000
    PROMETHEUS_PORT: int = 8001

    # Supabase
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None

    # Batch processing
    BATCH_CHUNK_SIZE: int = 500
    MAX_RETRIES: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = True

    @validator("GOOGLE_SHEETS_ID")
    def validate_sheet_id(cls, v):
        if v and len(v) < 10:  # Only validate if value is provided
            raise ValueError("GOOGLE_SHEETS_ID must be a valid Google Sheet ID")
        return v

    @validator("GMAIL_USER")
    def validate_email_sender(cls, v):
        if v:  # Only validate if value is provided
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError("GMAIL_USER must be a valid email address")
        return v

    @validator("KIXIE_API_KEY")
    def validate_kixie_key(cls, v):
        if v and len(v) < 10:  # Only validate if value is provided
            raise ValueError("KIXIE_API_KEY must be a valid API key")
        return v

    @validator("SUPABASE_URL")
    def validate_supabase_url(cls, v):
        if v and not v.startswith("https://"):  # Only validate if value is provided
            raise ValueError("SUPABASE_URL must be a valid HTTPS URL")
        return v

    @model_validator(mode="after")
    def validate_related_settings(self) -> 'Settings':
        """Validate that related settings are consistent."""
        # If email features are enabled, ensure sender is set
        if self.EMAIL_PASSWORD and not self.GMAIL_USER:
            raise ValueError("GMAIL_USER must be set when EMAIL_PASSWORD is provided")

        # If Supabase is enabled, ensure URL is valid
        if self.SUPABASE_SERVICE_KEY and not self.SUPABASE_URL:
            raise ValueError("SUPABASE_URL must be set when SUPABASE_SERVICE_KEY is provided")

        return self

    def validate_optional_settings(self) -> None:
        """Validate optional settings and log warnings for missing values."""
        # Google Sheets
        if not self.GOOGLE_SHEETS_CREDENTIALS:
            logger.warning("GOOGLE_SHEETS_CREDENTIALS is missing—Google Sheets features will be disabled!")
        if not self.GOOGLE_SHEETS_TOKEN:
            logger.warning("GOOGLE_SHEETS_TOKEN is missing—Google Sheets features will be disabled!")
        if not self.GOOGLE_SHEETS_ID:
            logger.warning("GOOGLE_SHEETS_ID is missing—Google Sheets features will be disabled!")

        # Email
        if not self.EMAIL_PASSWORD:
            logger.warning("EMAIL_PASSWORD is missing—email features will be disabled!")
        if not self.REPORT_EMAIL:
            logger.warning("REPORT_EMAIL is missing—daily reports will be disabled!")

        # SMS (Kixie)
        if not self.KIXIE_API_KEY:
            logger.warning("KIXIE_API_KEY is missing—SMS features will be disabled!")
        if not self.KIXIE_BASE_URL:
            logger.warning("KIXIE_BASE_URL is missing—SMS features will be disabled!")

        # Supabase
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
        logger.info(f"Email Features: {'Enabled' if self.EMAIL_PASSWORD else 'Disabled'}")
        logger.info(f"Supabase Features: {'Enabled' if self.SUPABASE_SERVICE_KEY else 'Disabled'}")
        logger.info(f"Google Sheets Integration: {'Enabled' if self.GOOGLE_SHEETS_CREDENTIALS else 'Disabled'}")
        logger.info(f"SMS Features: {'Enabled' if self.KIXIE_API_KEY else 'Disabled'}")


# Initialize settings and validate optional values
settings = Settings()
settings.validate_optional_settings()
settings.log_configuration()
