import logging
from datetime import datetime
from celery import chord
from prometheus_client import Counter, Histogram
from app.celery import celery
from app.config import settings
from app.models.lead import Lead
from app.services.batch_processor import BatchProcessor
from app.services.email_service import EmailService
from app.services.supabase_service import supabase_service
from app.services.timezone_utils import now_in_timezone
from app.utils.date_utils import format_date
from app.services.google_sheets import GoogleSheetsService

logger = logging.getLogger("lead_followup.scheduler")

# Metrics
task_duration = Histogram(
    "lead_task_duration_seconds",
    "Time taken to process each lead",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)
task_errors = Counter("lead_task_errors_total", "Lead processing failures")

@celery.task(name="app.scheduler.process_lead_task")
def process_lead_task(lead_data: dict) -> None:
    start_time = time.time()
    try:
        lead = Lead(**lead_data)
        now_tz = now_in_timezone(lead.area_code or settings.DEFAULT_AREA_CODE)
        today_str = format_date(now_tz)

        # Idempotency check
        if supabase_service.has_followup(lead.row_number, today_str):
            logger.info(f"Already processed lead {lead.row_number} for {today_str}")
            return

        # Process lead (email/SMS logic here)
        batch_processor = BatchProcessor()
        batch_processor.enqueue_update(lead.row_number, "Last Texted", today_str)
        batch_processor.enqueue_update(lead.row_number, "AI SUMMARY", "Summary here...")

        # Log to Supabase after successful enqueue
        supabase_service.log_followup(
            lead.row_number,
            "email_sms",
            today_str,
            lead.first_name,
            lead.company or ""
        )

    except Exception as e:
        logger.error(f"Lead processing failed: {e}")
        task_errors.inc()
        raise
    finally:
        task_duration.observe(time.time() - start_time)

@celery.task(name="app.scheduler.flush_and_summary")
def flush_and_summary(results: List[dict]) -> None:
    try:
        batch_processor = BatchProcessor()
        batch_processor.process_batch()
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        EmailService().send_email(
            settings.EMAIL_DAILY_REPORT_TO,
            "Critical: Sheets Batch Update Failed",
            f"Could not batch update: {e}"
        )
        return

    try:
        now_tz = now_in_timezone(settings.DEFAULT_AREA_CODE)
        today_str = format_date(now_tz)
        summary_list = supabase_service.get_today_followups(today_str)
        EmailService().send_daily_report(today_str, summary_list)
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        EmailService().send_email(
            settings.EMAIL_DAILY_REPORT_TO,
            "Critical: Summary Generation Failed",
            f"Could not generate summary: {e}"
        )

@celery.task(name="app.scheduler.handle_chord_error")
def handle_chord_error(request, exc, traceback):
    logger.error(f"Chord failed: {exc}")
    EmailService().send_email(
        settings.EMAIL_DAILY_REPORT_TO,
        "Critical: Daily Follow-up Failed",
        f"Chord failed: {exc}\n{traceback}"
    )

def run_daily_followups():
    try:
        batch_processor = BatchProcessor()
        batch_processor.redis.delete("sheets_batch")
    except Exception as e:
        logger.error(f"Redis flush failed: {e}")
        EmailService().send_email(
            settings.EMAIL_DAILY_REPORT_TO,
            "Critical: Redis Down",
            f"Could not flush Redis: {e}"
        )
        return

    try:
        sheets = GoogleSheetsService()
        leads = sheets.get_all_leads()
    except Exception as e:
        logger.error(f"Sheets fetch failed: {e}")
        EmailService().send_email(
            settings.EMAIL_DAILY_REPORT_TO,
            "Critical: Sheets Down",
            f"Could not fetch leads: {e}"
        )
        return

    # Use chord with error handling
    task_group = [process_lead_task.s(lead.dict()) for lead in leads]
    chord(task_group, flush_and_summary.s()).apply_async(
        link_error=handle_chord_error.s()
    )

if __name__ == "__main__":
    run_daily_followups()
