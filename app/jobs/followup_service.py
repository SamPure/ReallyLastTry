import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from app.services.config_manager import get_settings
from app.services.supabase_client import get_supabase_client
from app.services.email_service import email_service
from app.services.retry_logger import with_retry_logging, retry_logger
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler()

class FollowupService:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.email_service = email_service
        self.alert_threshold = settings.FOLLOWUP_QUEUE_ALERT_THRESHOLD
        self.metrics = {
            "total_followups": 0,
            "successful_followups": 0,
            "failed_followups": 0,
            "queued_followups": 0,
            "last_alert_time": None
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get follow-up service statistics."""
        return {
            "metrics": self.metrics,
            "retry_stats": retry_logger.get_stats(),
            "queue_size": self.metrics["queued_followups"],
            "alert_threshold": self.alert_threshold,
            "last_alert": self.metrics["last_alert_time"]
        }

    def check_alert_threshold(self) -> None:
        """Check if queue size exceeds alert threshold."""
        if self.metrics["queued_followups"] > self.alert_threshold:
            self.metrics["last_alert_time"] = datetime.utcnow().isoformat()
            logger.warning(
                f"Follow-up queue size ({self.metrics['queued_followups']}) exceeds threshold ({self.alert_threshold})"
            )

    @with_retry_logging(max_retries=3, job_name="send_followup")
    async def send_followup(self, lead_id: str, template_name: str, template_data: Dict[str, Any]) -> bool:
        """Send a follow-up email with retry logging."""
        try:
            # Get lead details
            lead = await self.supabase.get_lead(lead_id)
            if not lead:
                logger.error(f"Lead {lead_id} not found")
                return False

            # Check if within business hours
            if not self.email_service.is_within_business_hours():
                self.metrics["queued_followups"] += 1
                self.check_alert_threshold()
                logger.info(f"Queued follow-up for lead {lead_id} (outside business hours)")
                return True

            # Send email
            success = await self.email_service.send_email(
                to=lead["email"],
                subject=f"Follow-up: {template_data.get('subject', 'Regarding your inquiry')}",
                template_name=template_name,
                template_data={
                    **template_data,
                    "lead_id": lead_id,
                    "lead_name": lead.get("name", "there")
                }
            )

            if success:
                self.metrics["successful_followups"] += 1
                logger.info(f"Follow-up sent to lead {lead_id}")
            else:
                self.metrics["failed_followups"] += 1
                logger.error(f"Failed to send follow-up to lead {lead_id}")

            self.metrics["total_followups"] += 1
            return success

        except Exception as e:
            self.metrics["failed_followups"] += 1
            logger.error(f"Error sending follow-up to lead {lead_id}: {e}")
            raise

    async def process_followup_queue(self) -> None:
        """Process queued follow-ups during business hours."""
        if not self.email_service.is_within_business_hours():
            return

        try:
            # Get queued follow-ups
            queued = await self.supabase.get_queued_followups()

            for followup in queued:
                success = await self.send_followup(
                    lead_id=followup["lead_id"],
                    template_name=followup["template_name"],
                    template_data=followup["template_data"]
                )

                if success:
                    await self.supabase.mark_followup_sent(followup["id"])
                    self.metrics["queued_followups"] -= 1

        except Exception as e:
            logger.error(f"Error processing follow-up queue: {e}")

    def is_healthy(self) -> bool:
        """Check if follow-up service is healthy."""
        try:
            # Check if queue size is within acceptable range
            if self.metrics["queued_followups"] > self.alert_threshold * 2:
                return False

            # Check if we have recent successful follow-ups
            if self.metrics["total_followups"] > 0 and self.metrics["successful_followups"] == 0:
                return False

            return True
        except Exception as e:
            logger.error(f"Follow-up service health check failed: {e}")
            return False

@with_retry_logging(max_retries=3, job_name="monitor_queue_size")
async def _monitor_queue_size():
    """Monitor email queue size and process if needed."""
    try:
        email_service.check_alert_threshold()
        await email_service._process_email_queue()
    except Exception as e:
        logger.error(f"Error monitoring queue size: {str(e)}")
        raise

def start_scheduler():
    """Start the email scheduler."""
    try:
        # Add queue monitoring job
        scheduler.add_job(
            lambda: asyncio.create_task(_monitor_queue_size()),
            'interval',
            minutes=5,
            id='monitor_queue'
        )

        scheduler.start()
        logger.info("Email scheduler started")
    except Exception as e:
        logger.error(f"Failed to start email scheduler: {str(e)}")
        raise

# Initialize singleton instance
followup_service = FollowupService()
