from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import validator, EmailStr, HttpUrl
import json
import logging
from functools import lru_cache

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
    SUPABASE_KEY: str

    # Google Sheets
    GOOGLE_SHEETS_ID: str
    GOOGLE_SERVICE_ACCOUNT_INFO: Dict[str, Any]

    # Email Configuration
    EMAIL_FROM: EmailStr
    EMAIL_START_HOUR: int = 9
    EMAIL_END_HOUR: int = 17
    EMAIL_BATCH_SIZE: int = 50
    EMAIL_BATCH_DELAY: int = 1
    EMAIL_QUEUE_ALERT_THRESHOLD: int = 1000

    # Kixie SMS
    KIXIE_API_KEY: str
    KIXIE_WEBHOOK_SECRET: str

    # JWT
    JWT_SECRET: str
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

    @validator("GOOGLE_SERVICE_ACCOUNT_INFO", pre=True)
    def parse_google_credentials(cls, v):
        """Parse Google service account credentials from JSON string if needed."""
        if isinstance(v, str):
            try:
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
