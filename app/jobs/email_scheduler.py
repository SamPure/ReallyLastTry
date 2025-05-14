import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.config_manager import get_settings
from app.services.email_service import email_service

settings = get_settings()
logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

async def _process_queue() -> Dict[str, int]:
    """Process the email queue and return statistics."""
    logger.info("Starting queued email processing")
    start_time = datetime.now()

    try:
        # Get current queue size
        queue_size = len(email_service.email_queue)
        if not queue_size:
            logger.info("Email queue is empty")
            return {"processed": 0, "sent": 0, "failed": 0}

        logger.info(f"Processing {queue_size} queued emails")

        # Process in batches
        batch_size = settings.EMAIL_BATCH_SIZE
        results = {"processed": 0, "sent": 0, "failed": 0}

        for i in range(0, queue_size, batch_size):
            batch = email_service.email_queue[i:i + batch_size]
            tasks = []

            for email_data in batch:
                task = email_service.send_email(**email_data)
                tasks.append(task)

            # Process batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Update statistics
            for result in batch_results:
                results["processed"] += 1
                if isinstance(result, Exception):
                    results["failed"] += 1
                    logger.error(f"Failed to process email: {result}")
                elif result:
                    results["sent"] += 1
                else:
                    results["failed"] += 1

            # Rate limiting between batches
            if i + batch_size < queue_size:
                await asyncio.sleep(settings.EMAIL_BATCH_DELAY)

        # Log results
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            "Email queue processed in %.2f seconds. "
            "Processed: %d, Sent: %d, Failed: %d",
            duration,
            results["processed"],
            results["sent"],
            results["failed"]
        )

        return results

    except Exception as e:
        logger.error(f"Error processing email queue: {e}")
        return {"processed": 0, "sent": 0, "failed": 0}

async def _monitor_queue_size():
    """Monitor and log queue size periodically."""
    queue_size = len(email_service.email_queue)
    if queue_size > 0:
        logger.info(f"Current email queue size: {queue_size}")

    # Alert if queue is getting large
    if queue_size > settings.EMAIL_QUEUE_ALERT_THRESHOLD:
        logger.warning(
            f"Email queue size ({queue_size}) exceeds alert threshold "
            f"({settings.EMAIL_QUEUE_ALERT_THRESHOLD})"
        )

def start_email_scheduler():
    """Start the email scheduler with queue processing and monitoring jobs."""
    try:
        # Main queue processing job
        scheduler.add_job(
            lambda: asyncio.create_task(_process_queue()),
            CronTrigger(
                day_of_week="mon-fri",
                hour=f"{settings.EMAIL_START_HOUR}-{settings.EMAIL_END_HOUR}",
                minute=0
            ),
            id="email_queue_processor",
            replace_existing=True
        )

        # Queue monitoring job (runs every 15 minutes)
        scheduler.add_job(
            lambda: asyncio.create_task(_monitor_queue_size()),
            CronTrigger(minute="*/15"),
            id="email_queue_monitor",
            replace_existing=True
        )

        scheduler.start()
        logger.info(
            "Email scheduler started. Processing hours: %d-%d, "
            "Batch size: %d, Batch delay: %d seconds",
            settings.EMAIL_START_HOUR,
            settings.EMAIL_END_HOUR,
            settings.EMAIL_BATCH_SIZE,
            settings.EMAIL_BATCH_DELAY
        )

    except Exception as e:
        logger.error(f"Failed to start email scheduler: {e}")
        raise

def stop_email_scheduler():
    """Stop the email scheduler gracefully."""
    try:
        scheduler.shutdown()
        logger.info("Email scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping email scheduler: {e}")
        raise
