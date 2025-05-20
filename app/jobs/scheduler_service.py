import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.config_manager import get_settings
from app.services.supabase_client import get_supabase_client
from app.models.priority import priority_scorer

settings = get_settings()
scheduler = AsyncIOScheduler()
logger = logging.getLogger(__name__)

async def run_followups():
    logger.info("Computing lead priorities and enqueuing follow-ups")
    try:
        # fetch all active leads
        leads = await get_supabase_client().fetch_leads()  # Make this async
        tasks = []
        for lead in leads:
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

        await asyncio.gather(*tasks)
        logger.info(f"✅ Enqueued {len(tasks)} follow-ups")
    except Exception as e:
        logger.error(f"❌ Error running follow-ups: {e}")
        raise

async def send_followup(lead_id: str, score: float):
    # import here to avoid circular
    from app.services.ai_handler import generate_and_send_message
    try:
        await generate_and_send_message(lead_id, score)
        logger.info(f"✅ Follow-up sent to lead {lead_id}")
    except Exception as e:
        logger.error(f"❌ Failed to send follow-up to lead {lead_id}: {e}")
        raise

def start_scheduler():
    try:
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
