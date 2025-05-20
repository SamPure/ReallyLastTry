import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.config_manager import get_settings
from app.services.supabase_client import get_supabase_client
from app.models.priority import priority_scorer
from app.jobs.followup_service import followup_service

settings = get_settings()
scheduler = AsyncIOScheduler()
logger = logging.getLogger(__name__)

async def run_followups():
    logger.info("Computing lead priorities and enqueuing follow-ups")
    try:
        # fetch all active leads
        try:
            leads = await get_supabase_client().fetch_leads()
        except Exception as e:
            logger.exception("Failed to fetch leads: %s", e)
            raise

        tasks = []
        for lead in leads:
            try:
                # respect 24h throttle
                last = await get_supabase_client().fetch_recent_conversations(lead["id"], limit=1)
                if last:
                    last_ts = datetime.fromisoformat(last[0]["timestamp"])
                    if (datetime.utcnow() - last_ts).total_seconds() < settings.FOLLOWUP_THROTTLE_SECONDS:
                        continue

                score = priority_scorer.compute(lead)
                if score < settings.FOLLOWUP_MIN_SCORE:
                    continue
                # schedule message
                tasks.append(asyncio.create_task(
                    send_followup(lead["id"], score)
                ))
            except Exception as e:
                logger.exception("Failed to process lead %s: %s", lead["id"], e)
                continue

        if tasks:
            try:
                await asyncio.gather(*tasks)
                logger.info(f"✅ Enqueued {len(tasks)} follow-ups")
            except Exception as e:
                logger.exception("Failed to process follow-up tasks: %s", e)
                raise
        else:
            logger.info("No follow-ups to enqueue")
    except Exception as e:
        logger.exception("Follow-up batch job crashed: %s", e)
        raise

async def send_followup(lead_id: str, score: float):
    try:
        # Use the followup service to send the message
        success = await followup_service.send_followup(
            lead_id=lead_id,
            template_name="followup",
            template_data={"priority_score": score}
        )
        if success:
            logger.info(f"✅ Follow-up sent to lead {lead_id}")
        else:
            logger.error(f"❌ Failed to send follow-up to lead {lead_id}")
    except Exception as e:
        logger.error(f"❌ Failed to send follow-up to lead {lead_id}: {e}")
        raise

def start_scheduler():
    try:
        # Start the followup service first
        followup_service.start()
        
        # run every business hour
        scheduler.add_job(
            lambda: asyncio.create_task(run_followups()),
            "cron",
            day_of_week="mon-fri",
            hour=f"{settings.FOLLOWUP_START_HOUR}-{settings.FOLLOWUP_END_HOUR}",
            minute=0,
            id="followup_scheduler"
        )
        logger.info("✅ Follow-up batch job scheduled")
        scheduler.start()
        logger.info("✅ Follow-up scheduler started")
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")
        raise

def is_healthy() -> bool:
    """Check if the scheduler is healthy."""
    try:
        if not scheduler.running:
            logger.error("Main scheduler is not running")
            return False
            
        if not followup_service.is_healthy():
            logger.error("Followup service is not healthy")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Scheduler health check failed: {e}")
        return False
