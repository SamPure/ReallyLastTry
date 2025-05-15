import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.config_manager import get_settings
from app.services.supabase_client import get_supabase_client
from app.models.priority import priority_scorer

settings = get_settings()
scheduler = AsyncIOScheduler()

async def run_followups():
    logging.info("Computing lead priorities and enqueuing follow-ups")
    # fetch all active leads
    leads = get_supabase_client().fetch_leads()  # synchronous call; wrap if needed
    tasks = []
    for lead in leads:
        # respect 24h throttle
        last = get_supabase_client().fetch_recent_conversations(lead["id"], limit=1)
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
    logging.info("Enqueued %d follow-ups", len(tasks))

async def send_followup(lead_id: str, score: float):
    # import here to avoid circular
    from app.services.ai_handler import generate_and_send_message
    await generate_and_send_message(lead_id, score)

def start_scheduler():
    # run every business hour
    scheduler.add_job(
        lambda: asyncio.create_task(run_followups()),
        "cron",
        day_of_week="mon-fri",
        hour=f"{settings.FOLLOWUP_START_HOUR}-{settings.FOLLOWUP_END_HOUR}",
        minute=0,
        id="followup_scheduler"
    )
    scheduler.start()
    logging.info("Follow-up scheduler started")
