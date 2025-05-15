from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import validator, EmailStr, HttpUrl, Field
import json
import logging
from functools import lru_cache
import os

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Environment
    ENV: str = "development"
    DEBUG: bool = True

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

    # Kixie SMS Configuration
    KIXIE_BASE_URL: str = Field(default="https://api.kixie.com/v1")
    KIXIE_API_KEY: str = Field(default="")
    KIXIE_SECRET: str = Field(default="")
    KIXIE_BUSINESS_ID: str = Field(default="")

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

    # Priority Scoring Settings
    PRIORITY_RECENCY_WEIGHT: float = Field(0.5)
    PRIORITY_ENGAGEMENT_WEIGHT: float = Field(0.3)
    PRIORITY_CLASS_WEIGHT: float = Field(0.2)
    PRIORITY_RECENCY_HALF_LIFE_DAYS: int = Field(7)
    PRIORITY_ENGAGEMENT_WINDOW_DAYS: int = Field(14)
    PRIORITY_CLASS_SCORES: dict = Field(default_factory=lambda: {
        "hot": 1.0,
        "warm": 0.7,
        "cold": 0.3,
        "default": 0.5
    })

    # Follow-up Configuration
    FOLLOWUP_START_HOUR: int = Field(default=9, description="Hour to start follow-ups (0-23)")
    FOLLOWUP_END_HOUR: int = Field(default=17, description="Hour to end follow-ups (0-23)")
    FOLLOWUP_QUEUE_ALERT_THRESHOLD: int = Field(default=100)
    FOLLOWUP_BATCH_SIZE: int = Field(default=50)
    FOLLOWUP_RETRY_DELAY: int = Field(default=300)

    @validator("GOOGLE_CREDENTIALS", pre=True)
    def parse_google_credentials(cls, v):
        """Parse Google service account credentials from JSON string if needed, handling escaped newlines."""
        if isinstance(v, str):
            try:
                # Replace escaped \n with real newlines for private_key
                v = v.replace('\\n', '\n')
                return json.loads(v)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid Google service account JSON: {e}")
        return v

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string if needed."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        case_sensitive = True
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    try:
        settings = Settings()
        logger.info(f"Loaded settings for environment: {settings.ENV}")
        return settings
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        raise

# Initialize settings
settings = get_settings()
