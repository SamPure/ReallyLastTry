import os
import pytest
from app.config import Settings

def test_required_settings():
    """Test that required settings raise errors when missing."""
    with pytest.raises(ValueError):
        Settings(
            SHEET_ID="",  # Invalid sheet ID
            EMAIL_SENDER="invalid-email",  # Invalid email
            KIXIE_API_KEY="short",  # Invalid API key
            GOOGLE_CREDENTIALS="{}",  # Valid JSON but empty
            SUPABASE_URL="https://example.supabase.co",
            KIXIE_BASE_URL="https://api.kixie.com",
            KIXIE_BUSINESS_ID="123"
        )

def test_optional_settings():
    """Test that optional settings work correctly when missing."""
    settings = Settings(
        SHEET_ID="12345678901234567890",
        EMAIL_SENDER="test@example.com",
        KIXIE_API_KEY="valid_api_key_12345",
        GOOGLE_CREDENTIALS='{"type": "service_account"}',
        SUPABASE_URL="https://example.supabase.co",
        KIXIE_BASE_URL="https://api.kixie.com",
        KIXIE_BUSINESS_ID="123",
        # Optional settings omitted
    )

    assert settings.EMAIL_API_KEY is None
    assert settings.EMAIL_DAILY_REPORT_TO is None
    assert settings.SUPABASE_KEY is None
    assert settings.supabase_client is None

def test_google_credentials_parsing():
    """Test Google credentials JSON parsing."""
    valid_creds = '{"type": "service_account", "project_id": "test"}'
    settings = Settings(
        SHEET_ID="12345678901234567890",
        EMAIL_SENDER="test@example.com",
        KIXIE_API_KEY="valid_api_key_12345",
        GOOGLE_CREDENTIALS=valid_creds,
        SUPABASE_URL="https://example.supabase.co",
        KIXIE_BASE_URL="https://api.kixie.com",
        KIXIE_BUSINESS_ID="123"
    )

    assert settings.google_credentials["type"] == "service_account"
    assert settings.google_credentials["project_id"] == "test"

def test_invalid_google_credentials():
    """Test that invalid Google credentials raise an error."""
    with pytest.raises(ValueError):
        Settings(
            SHEET_ID="12345678901234567890",
            EMAIL_SENDER="test@example.com",
            KIXIE_API_KEY="valid_api_key_12345",
            GOOGLE_CREDENTIALS="invalid-json",
            SUPABASE_URL="https://example.supabase.co",
            KIXIE_BASE_URL="https://api.kixie.com",
            KIXIE_BUSINESS_ID="123"
        )

def test_redis_url_fallback():
    """Test Redis URL fallback to default value."""
    settings = Settings(
        SHEET_ID="12345678901234567890",
        EMAIL_SENDER="test@example.com",
        KIXIE_API_KEY="valid_api_key_12345",
        GOOGLE_CREDENTIALS='{"type": "service_account"}',
        SUPABASE_URL="https://example.supabase.co",
        KIXIE_BASE_URL="https://api.kixie.com",
        KIXIE_BUSINESS_ID="123"
    )

    assert settings.CELERY_BROKER_URL == "redis://localhost:6379/0"

def test_redis_url_override():
    """Test Redis URL override from environment."""
    os.environ["REDIS_URL"] = "redis://custom:6379/0"
    settings = Settings(
        SHEET_ID="12345678901234567890",
        EMAIL_SENDER="test@example.com",
        KIXIE_API_KEY="valid_api_key_12345",
        GOOGLE_CREDENTIALS='{"type": "service_account"}',
        SUPABASE_URL="https://example.supabase.co",
        KIXIE_BASE_URL="https://api.kixie.com",
        KIXIE_BUSINESS_ID="123"
    )

    assert settings.CELERY_BROKER_URL == "redis://custom:6379/0"
    del os.environ["REDIS_URL"]
