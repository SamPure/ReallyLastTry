import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, time
from app.services.email_service import EmailService, email_service
from app.services.config_manager import get_settings

@pytest.fixture
def mock_gmail_service():
    """Create a mock Gmail service."""
    with patch('app.services.email_service.build') as mock_build:
        mock_service = Mock()
        mock_service.users().messages().send().execute.return_value = {'id': 'test_message_id'}
        mock_build.return_value = mock_service
        yield mock_service

@pytest.fixture
def mock_settings():
    """Create mock settings."""
    with patch('app.services.email_service.get_settings') as mock_get_settings:
        settings = Mock()
        settings.EMAIL_SENDER = "test@example.com"
        settings.EMAIL_START_HOUR = 9
        settings.EMAIL_END_HOUR = 17
        settings.EMAIL_BATCH_SIZE = 50
        settings.EMAIL_QUEUE_ALERT_THRESHOLD = 100
        mock_get_settings.return_value = settings
        yield settings

@pytest.mark.asyncio
async def test_email_service_initialization(mock_gmail_service, mock_settings):
    """Test email service initialization."""
    service = EmailService()
    assert service.gmail_service is not None
    assert service.sender_email == "test@example.com"

@pytest.mark.asyncio
async def test_send_email_success(mock_gmail_service, mock_settings):
    """Test successful email sending."""
    service = EmailService()

    # Mock current time to be within business hours
    with patch('app.services.email_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0)  # 10 AM

        success = await service.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test Body"
        )

        assert success is True
        mock_gmail_service.users().messages().send.assert_called_once()

@pytest.mark.asyncio
async def test_send_email_outside_business_hours(mock_gmail_service, mock_settings):
    """Test email queuing outside business hours."""
    service = EmailService()

    # Mock current time to be outside business hours
    with patch('app.services.email_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 1, 1, 8, 0)  # 8 AM

        success = await service.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test Body",
            schedule=True
        )

        assert success is True
        assert len(service.email_queue) == 1
        mock_gmail_service.users().messages().send.assert_not_called()

@pytest.mark.asyncio
async def test_send_email_retry(mock_gmail_service, mock_settings):
    """Test email sending with retries."""
    service = EmailService()

    # Mock Gmail service to fail twice then succeed
    attempt = 0
    def mock_send(*args, **kwargs):
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            raise Exception("Simulated Gmail error")
        return {'id': 'test_message_id'}

    mock_gmail_service.users().messages().send().execute.side_effect = mock_send

    # Mock current time to be within business hours
    with patch('app.services.email_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0)  # 10 AM

        success = await service.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test Body"
        )

        assert success is True
        assert attempt == 3

@pytest.mark.asyncio
async def test_process_email_queue(mock_gmail_service, mock_settings):
    """Test processing of email queue."""
    service = EmailService()

    # Add test emails to queue
    service.email_queue = [
        {
            "to": "test1@example.com",
            "subject": "Test 1",
            "body": "Body 1"
        },
        {
            "to": "test2@example.com",
            "subject": "Test 2",
            "body": "Body 2"
        }
    ]

    # Mock current time to be within business hours
    with patch('app.services.email_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0)  # 10 AM

        await service._process_email_queue()

        assert len(service.email_queue) == 0
        assert mock_gmail_service.users().messages().send.call_count == 2

@pytest.mark.asyncio
async def test_alert_threshold(mock_gmail_service, mock_settings):
    """Test email queue alert threshold."""
    service = EmailService()

    # Add emails to exceed threshold
    for i in range(mock_settings.EMAIL_QUEUE_ALERT_THRESHOLD + 1):
        service.email_queue.append({
            "to": f"test{i}@example.com",
            "subject": f"Test {i}",
            "body": f"Body {i}"
        })

    # Check alert threshold
    service.check_alert_threshold()
    assert service.metrics["last_alert_time"] is not None

@pytest.mark.asyncio
async def test_health_check(mock_gmail_service, mock_settings):
    """Test email service health check."""
    service = EmailService()

    # Test healthy state
    assert service.is_healthy() is True

    # Test unhealthy state (queue too large)
    service.email_queue = [{"to": "test@example.com"}] * (mock_settings.EMAIL_QUEUE_ALERT_THRESHOLD * 2)
    assert service.is_healthy() is False

@pytest.mark.asyncio
async def test_business_hours_check(mock_gmail_service, mock_settings):
    """Test business hours checking."""
    service = EmailService()

    # Test within business hours
    with patch('app.services.email_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0)  # 10 AM
        assert service.is_within_business_hours() is True

        # Test outside business hours
        mock_datetime.now.return_value = datetime(2024, 1, 1, 8, 0)  # 8 AM
        assert service.is_within_business_hours() is False
