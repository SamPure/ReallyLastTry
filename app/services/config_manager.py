from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import validator, EmailStr, HttpUrl, Field, model_validator
import json
import logging
import re
from functools import lru_cache
import os

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Environment
    ENV: str = "development"
    DEBUG: bool = True
    ENVIRONMENT: str = "production"
    DEFAULT_AREA_CODE: str = "212"

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Pure Financial Funding"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: Optional[str] = None

    # Google Sheets
    SHEET_ID: Optional[str] = None
    GOOGLE_CREDENTIALS: Optional[str] = None
    GOOGLE_SHEETS_CREDENTIALS_JSON: str = Field(default="")
    LEADS_SHEET_NAME: str = Field(default="Leads")
    TONE_SETTINGS_SHEET_NAME: str = Field(default="BrokerTones")
    GOOGLE_SHEETS_LEADS_RANGE: str = Field(default="A1:Z1000")
    GOOGLE_SHEETS_TONE_RANGE: str = Field(default="A1:Z100")

    # Email Configuration
    EMAIL_SENDER: Optional[str] = None
    EMAIL_START_HOUR: int = 9
    EMAIL_END_HOUR: int = 17
    EMAIL_BATCH_SIZE: int = 50
    EMAIL_BATCH_DELAY: int = 1
    EMAIL_QUEUE_ALERT_THRESHOLD: int = 1000
    EMAIL_PASSWORD: Optional[str] = None
    REPORT_EMAIL: Optional[str] = None
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587

    # Gmail Configuration
    GMAIL_USER: Optional[str] = None
    GMAIL_CLIENT_ID: Optional[str] = None
    GMAIL_CLIENT_SECRET: Optional[str] = None
    GMAIL_REFRESH_TOKEN: Optional[str] = None
    GMAIL_APP_PASSWORD: Optional[str] = None

    # Kixie SMS Configuration
    KIXIE_BASE_URL: str = Field(default="https://api.kixie.com/v1")
    KIXIE_API_KEY: str = Field(default="")
    KIXIE_SECRET: str = Field(default="")
    KIXIE_BUSINESS_ID: str = Field(default="")

    # Core Infrastructure
    PORT: int = 8000
    PROMETHEUS_PORT: int = 8001

    # JWT
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Feature Flags
    ENABLE_GOOGLE_SHEETS_SYNC: bool = True
    ENABLE_EMAIL_FALLBACK: bool = True
    ENABLE_DAILY_REPORTS: bool = True

    # Business Hours
    BUSINESS_HOURS_START: int = 9
    BUSINESS_HOURS_END: int = 17

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Batch Processing
    BATCH_SIZE: int = 100
    BATCH_DELAY: int = 1
    BATCH_CHUNK_SIZE: int = 500
    MAX_RETRIES: int = 3

    # Priority Scoring Settings
    PRIORITY_RECENCY_WEIGHT: float = 0.5
    PRIORITY_ENGAGEMENT_WEIGHT: float = 0.3
    PRIORITY_CLASS_WEIGHT: float = 0.2
    PRIORITY_RECENCY_HALF_LIFE_DAYS: int = 7
    PRIORITY_ENGAGEMENT_WINDOW_DAYS: int = 14
    PRIORITY_CLASS_SCORES: dict = {
        "hot": 1.0,
        "warm": 0.7,
        "cold": 0.3,
        "default": 0.5
    }

    class Config:
        env_file = ".env"
        case_sensitive = True

    @validator("SHEET_ID")
    def validate_sheet_id(cls, v):
        if v and len(v) < 10:  # Only validate if value is provided
            raise ValueError("SHEET_ID must be a valid Google Sheet ID")
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
        if not self.GOOGLE_CREDENTIALS:
            logger.warning("GOOGLE_CREDENTIALS is missing—Google Sheets features will be disabled!")
        if not self.SHEET_ID:
            logger.warning("SHEET_ID is missing—Google Sheets features will be disabled!")

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

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

# Initialize settings
settings = get_settings()
