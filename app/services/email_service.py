import logging
import asyncio
from datetime import datetime, time
from typing import Dict, Any, List, Optional, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from jinja2 import Environment, FileSystemLoader, select_autoescape
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import json
import os
import smtplib
from app.services.config_manager import get_settings
from app.services.supabase_client import get_supabase_client
from app.services.retry_logger import with_retry_logging, retry_logger

settings = get_settings()
logger = logging.getLogger(__name__)

# Initialize Jinja2 environment
env = Environment(
    loader=FileSystemLoader("app/templates/email"),
    autoescape=select_autoescape(["html", "xml"])
)

class EmailMetrics:
    """Track email sending metrics."""
    def __init__(self):
        self.total_sent = 0
        self.total_failed = 0
        self.total_retried = 0
        self.current_queue_size = 0
        self.current_retry_size = 0
        self.last_success_time = None
        self.last_error_time = None
        self.last_error_message = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_sent": self.total_sent,
            "total_failed": self.total_failed,
            "total_retried": self.total_retried,
            "current_queue_size": self.current_queue_size,
            "current_retry_size": self.current_retry_size,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "last_error_message": self.last_error_message
        }

class EmailService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.email_queue: List[Dict[str, Any]] = []
        self.retry_queue: List[Dict[str, Any]] = []  # Queue for failed sends
        self.metrics = EmailMetrics()
        self._setup_scheduler()
        self._initialize_gmail_service()
        self._rate_limiter = asyncio.Semaphore(settings.RATE_LIMIT_PER_MINUTE)
        self._max_retries = 3  # Maximum number of retry attempts
        self._base_delay = 1  # Base delay in seconds for exponential backoff
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = settings.EMAIL_SENDER
        self.settings = get_settings()
        self.gmail_service = None

    def _initialize_gmail_service(self):
        """Initialize Gmail API service."""
        try:
            if not self.settings.GOOGLE_SHEETS_CREDENTIALS_JSON:
                logger.warning("No Gmail credentials provided, email service will be disabled")
                return

            credentials_json = json.loads(self.settings.GOOGLE_SHEETS_CREDENTIALS_JSON)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_json,
                scopes=['https://www.googleapis.com/auth/gmail.send']
            )
            self.gmail_service = build('gmail', 'v1', credentials=credentials)
            logger.info("Gmail service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            self.gmail_service = None

    def _setup_scheduler(self):
        """Configure the scheduler for batch email processing."""
        # Run every hour during business hours
        self.scheduler.add_job(
            self._process_email_queue,
            CronTrigger(
                day_of_week="mon-fri",
                hour=f"{settings.EMAIL_START_HOUR}-{settings.EMAIL_END_HOUR}",
                minute=0
            ),
            id="email_batch_processor"
        )

        # Run retry queue processing every 15 minutes
        self.scheduler.add_job(
            self._process_retry_queue,
            CronTrigger(minute="*/15"),
            id="email_retry_processor"
        )

        # Update metrics every minute
        self.scheduler.add_job(
            self._update_metrics,
            CronTrigger(minute="*"),
            id="metrics_updater"
        )

        self.scheduler.start()
        logger.info("Email scheduler started")

    def _update_metrics(self):
        """Update current metrics."""
        self.metrics.current_queue_size = len(self.email_queue)
        self.metrics.current_retry_size = len(self.retry_queue)
        logger.debug(f"Updated metrics: {self.metrics.to_dict()}")

    async def _process_email_queue(self):
        """Process queued emails during business hours."""
        if not self.email_queue:
            return

        logger.info(f"Processing {len(self.email_queue)} queued emails")
        for email_data in self.email_queue[:]:
            try:
                await self.send_email(**email_data)
                self.email_queue.remove(email_data)
            except Exception as e:
                logger.error(f"Failed to process queued email: {e}")

    async def _process_retry_queue(self):
        """Process retry queue with exponential backoff."""
        if not self.retry_queue:
            return

        logger.info(f"Processing {len(self.retry_queue)} retry emails")
        for retry_data in self.retry_queue[:]:
            try:
                # Calculate exponential backoff delay
                retry_count = retry_data.get('retry_count', 0)
                delay = self._base_delay * (2 ** retry_count)

                # Wait for the calculated delay
                await asyncio.sleep(delay)

                # Attempt to send again
                success = await self.send_email(**retry_data['email_data'])

                if success:
                    self.retry_queue.remove(retry_data)
                    logger.info(f"Successfully sent retry email to {retry_data['email_data']['to']}")
                else:
                    # Update retry count and remove if max retries reached
                    retry_data['retry_count'] = retry_count + 1
                    if retry_count + 1 >= self._max_retries:
                        self.retry_queue.remove(retry_data)
                        logger.error(f"Max retries reached for email to {retry_data['email_data']['to']}")
            except Exception as e:
                logger.error(f"Failed to process retry email: {e}")

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current status of email queues and metrics."""
        return {
            "metrics": self.metrics.to_dict(),
            "queue_size": len(self.email_queue),
            "retry_queue_size": len(self.retry_queue),
            "next_retry_time": datetime.now().replace(minute=15 * (datetime.now().minute // 15 + 1), second=0, microsecond=0).isoformat() if self.retry_queue else None,
            "is_business_hours": (
                settings.EMAIL_START_HOUR <= datetime.now().hour <= settings.EMAIL_END_HOUR
                and datetime.now().weekday() < 5
            )
        }

    def _create_message(
        self,
        to: str,
        subject: str,
        template_name: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None,
        body: Optional[str] = None
    ) -> MIMEMultipart:
        """Create an email message with optional templating."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = to

        if template_name and template_data:
            template = env.get_template(f"{template_name}.html")
            html_content = template.render(**template_data)
            msg.attach(MIMEText(html_content, "html"))
        elif body:
            msg.attach(MIMEText(body, "plain"))
        else:
            raise ValueError("Either template_name/template_data or body must be provided")

        return msg

    async def _send_via_gmail(self, msg: MIMEMultipart) -> Tuple[bool, Optional[str], Optional[str]]:
        """Send email via Gmail API with rate limiting and error handling."""
        if not self.gmail_service:
            logger.warning("Gmail service not initialized. Email not sent.")
            return False, None, "Gmail service not initialized"

        async with self._rate_limiter:
            try:
                # Convert to raw message
                raw_message = msg.as_bytes()
                raw_message = raw_message.decode('utf-8')
                raw_message = raw_message.replace('\n', '\r\n').encode('utf-8')

                # Send via Gmail API
                message = self.gmail_service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute()

                return True, message['id'], None
            except HttpError as e:
                error_msg = f"Gmail API error: {e}"
                logger.error(error_msg)
                self.metrics.last_error_time = datetime.now()
                self.metrics.last_error_message = error_msg
                return False, None, error_msg
            except Exception as e:
                error_msg = f"Unexpected error: {e}"
                logger.error(error_msg)
                self.metrics.last_error_time = datetime.now()
                self.metrics.last_error_message = error_msg
                return False, None, error_msg

    @with_retry_logging(max_retries=3, job_name="send_email")
    async def send_email(
        self,
        to: str,
        subject: str,
        template_name: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None,
        body: Optional[str] = None,
        schedule: bool = False,
        retry_count: int = 0
    ) -> bool:
        """
        Send an email using Gmail API with optional templating and scheduling.

        Args:
            to: Recipient email address
            subject: Email subject
            template_name: Name of the Jinja2 template (without .html)
            template_data: Data to render in the template
            body: Plain text body (if no template)
            schedule: Whether to queue for scheduled sending
            retry_count: Number of retry attempts (internal use)

        Returns:
            bool: True if email was sent or queued successfully
        """
        try:
            # Check if we should queue the email
            current_hour = datetime.now().hour
            if schedule and not (
                settings.EMAIL_START_HOUR <= current_hour <= settings.EMAIL_END_HOUR
                and datetime.now().weekday() < 5  # Mon-Fri
            ):
                self.email_queue.append({
                    "to": to,
                    "subject": subject,
                    "template_name": template_name,
                    "template_data": template_data,
                    "body": body
                })
                logger.info(f"Queued email to {to} for business hours")
                return True

            # Create the message
            msg = self._create_message(
                to=to,
                subject=subject,
                template_name=template_name,
                template_data=template_data,
                body=body
            )

            # Send via Gmail API
            success, message_id, error = await self._send_via_gmail(msg)
            if not success:
                # Add to retry queue if not at max retries
                if retry_count < self._max_retries:
                    self.retry_queue.append({
                        'email_data': {
                            'to': to,
                            'subject': subject,
                            'template_name': template_name,
                            'template_data': template_data,
                            'body': body,
                            'schedule': schedule,
                            'retry_count': retry_count + 1
                        },
                        'retry_count': retry_count
                    })
                    self.metrics.total_retried += 1
                    logger.info(f"Added email to retry queue for {to}")
                else:
                    self.metrics.total_failed += 1
                    logger.error(f"Failed to send email to {to} after {retry_count} retries: {error}")
                return False

            # Update metrics
            self.metrics.total_sent += 1
            self.metrics.last_success_time = datetime.now()

            # Log to Supabase if available
            if get_supabase_client() and template_data and "lead_id" in template_data:
                get_supabase_client().insert_conversation(
                    lead_id=template_data["lead_id"],
                    message=f"Email sent: {subject}",
                    direction="outbound",
                    status="sent",
                    metadata={
                        "email_subject": subject,
                        "template": template_name,
                        "message_id": message_id,
                        **template_data
                    }
                )

            logger.info(f"Email sent to {to} (message_id: {message_id})")
            return True

        except Exception as e:
            self.metrics.total_failed += 1
            self.metrics.last_error_time = datetime.now()
            self.metrics.last_error_message = str(e)
            logger.error(f"Failed to send email to {to}: {e}")
            return False

    async def send_bulk_emails(
        self,
        recipients: List[Dict[str, Any]],
        subject: str,
        template_name: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None,
        body: Optional[str] = None,
        batch_size: int = 50
    ) -> Dict[str, int]:
        """
        Send emails to multiple recipients in batches.

        Args:
            recipients: List of dicts with 'email' and optional 'data' keys
            subject: Email subject
            template_name: Name of the Jinja2 template
            template_data: Base template data
            body: Plain text body (if no template)
            batch_size: Number of emails to send per batch

        Returns:
            Dict with success and failure counts
        """
        results = {"success": 0, "failure": 0}

        for i in range(0, len(recipients), batch_size):
            batch = recipients[i:i + batch_size]
            tasks = []

            for recipient in batch:
                # Merge recipient-specific data with base template data
                merged_data = {
                    **(template_data or {}),
                    **(recipient.get("data", {}))
                } if template_data else recipient.get("data")

                task = self.send_email(
                    to=recipient["email"],
                    subject=subject,
                    template_name=template_name,
                    template_data=merged_data,
                    body=body,
                    schedule=True  # Always schedule bulk sends
                )
                tasks.append(task)

            # Wait for batch to complete
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successes and failures
            for result in batch_results:
                if isinstance(result, Exception):
                    results["failure"] += 1
                elif result:
                    results["success"] += 1
                else:
                    results["failure"] += 1

            # Rate limiting
            if i + batch_size < len(recipients):
                await asyncio.sleep(settings.EMAIL_BATCH_DELAY)

        return results

    def shutdown(self):
        """Clean up resources."""
        self.scheduler.shutdown()
        logger.info("Email scheduler stopped")

    def is_healthy(self) -> bool:
        """Check if the email service is healthy."""
        try:
            # Check if we have required configuration
            if not self.sender_email:
                return False

            # Check if queue processing is working
            if len(self.email_queue) > settings.EMAIL_QUEUE_ALERT_THRESHOLD:
                return False

            # Check if we have recent successful sends
            if self.metrics.total_sent == 0 and self.metrics.total_failed > 0:
                return False

            return True
        except Exception as e:
            logger.error(f"Email service health check failed: {str(e)}")
            return False

    def is_within_business_hours(self) -> bool:
        """Check if current time is within business hours."""
        current_time = datetime.now().time()
        return (
            self.settings.FOLLOWUP_START_HOUR <= current_time.hour < self.settings.FOLLOWUP_END_HOUR
        )

    async def schedule_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        template_data: Dict[str, Any],
        scheduled_time: datetime
    ) -> bool:
        """Schedule an email for later delivery."""
        try:
            # Store in database or queue
            # Implementation depends on your scheduling system
            logger.info(f"Email scheduled for {scheduled_time}")
            return True
        except Exception as e:
            logger.error(f"Failed to schedule email: {str(e)}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get email service statistics including retry/failure counts."""
        return {
            "service_initialized": self.gmail_service is not None,
            "retry_stats": retry_logger.get_stats()
        }

# Initialize singleton instance
email_service = EmailService()
