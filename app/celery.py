from celery import Celery
from app.services.config_manager import settings

celery = Celery(
    "lead_followup",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_BROKER_URL,
)

celery.conf.task_routes = {
    "app.scheduler.process_lead_task": {"queue": "followups"},
    "app.scheduler.flush_and_summary": {"queue": "followups"},
    "app.scheduler.handle_chord_error": {"queue": "followups"},
}
