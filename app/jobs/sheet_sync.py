from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from app.services.config_manager import settings
from app.services.supabase_client import supabase_client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from app.services.google_sheets import google_sheets, get_google_sheets_service
from app.services.config_manager import get_settings
import asyncio
import time

logger = logging.getLogger(__name__)

class SheetSync:
    def __init__(self):
        self.client = None
        self.worksheet = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Google Sheets client."""
        if not settings.GOOGLE_SHEETS_CREDENTIALS_JSON:
            logger.warning("Google Sheets credentials not configured")
            return

        try:
            credentials_dict = json.loads(settings.GOOGLE_SHEETS_CREDENTIALS_JSON)
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.client = gspread.authorize(credentials)

            if settings.SHEET_ID:
                spreadsheet = self.client.open_by_key(settings.SHEET_ID)
                self.worksheet = spreadsheet.worksheet(settings.LEADS_SHEET_NAME)
                logger.info("Google Sheets client initialized successfully")
            else:
                logger.warning("Google Sheets ID not configured")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            self.client = None
            self.worksheet = None

    def fetch_leads_sheet(self) -> List[Dict[str, Any]]:
        """Fetch all leads from the Google Sheet."""
        if not self.worksheet:
            logger.warning("Google Sheets worksheet not initialized")
            return []

        try:
            # Get all records
            records = self.worksheet.get_all_records()

            # Transform to our format
            leads = []
            for record in records:
                lead = {
                    "id": str(record.get("ID", "")),
                    "name": record.get("Name", ""),
                    "phone": record.get("Phone", ""),
                    "email": record.get("Email", ""),
                    "status": record.get("Status", "New"),
                    "last_contact": record.get("Last Contact", ""),
                    "notes": record.get("Notes", ""),
                    "metadata": {
                        "source": record.get("Source", ""),
                        "priority": record.get("Priority", "Medium"),
                        "assigned_to": record.get("Assigned To", "")
                    }
                }
                leads.append(lead)

            return leads
        except Exception as e:
            logger.error(f"Failed to fetch leads from sheet: {e}")
            return []

    def update_lead_status(
        self,
        lead_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update lead status in the Google Sheet."""
        if not self.worksheet:
            logger.warning("Google Sheets worksheet not initialized")
            return False

        try:
            # Find the row with matching ID
            cell = self.worksheet.find(lead_id)
            if not cell:
                logger.warning(f"Lead ID {lead_id} not found in sheet")
                return False

            # Update status and notes
            row = cell.row
            self.worksheet.update_cell(row, 5, status)  # Status column
            if notes:
                self.worksheet.update_cell(row, 7, notes)  # Notes column
            self.worksheet.update_cell(row, 6, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))  # Last Contact

            # Also update in Supabase if available
            if supabase_client:
                supabase_client.update_lead_status(lead_id, status, {"notes": notes})

            return True
        except Exception as e:
            logger.error(f"Failed to update lead status in sheet: {e}")
            return False

    def sync_broker_tone_settings(self) -> Dict[str, Any]:
        """Sync broker tone settings from a dedicated worksheet."""
        if not self.client or not settings.SHEET_ID:
            logger.warning("Google Sheets client not initialized")
            return {}

        try:
            spreadsheet = self.client.open_by_key(settings.SHEET_ID)
            tone_worksheet = spreadsheet.worksheet("BrokerTones")

            # Get all tone settings
            records = tone_worksheet.get_all_records()

            # Transform to our format
            tones = {}
            for record in records:
                broker_id = record.get("BrokerID", "")
                if broker_id:
                    tones[broker_id] = {
                        "tone": record.get("Tone", "Professional"),
                        "language": record.get("Language", "English"),
                        "custom_phrases": record.get("CustomPhrases", "").split(","),
                        "response_time": record.get("ResponseTime", "24h")
                    }

            return tones
        except Exception as e:
            logger.error(f"Failed to sync broker tone settings: {e}")
            return {}

    def is_healthy(self) -> bool:
        """Check if the Google Sheets sync service is healthy."""
        try:
            # Check if we have required configuration
            if not settings.SHEET_ID or not settings.GOOGLE_CREDENTIALS:
                return False

            # Check if we have a valid credentials object
            if not self.client or not self.client.credentials or not self.client.credentials.valid:
                return False

            return True
        except Exception as e:
            logger.error(f"Sheet sync health check failed: {str(e)}")
            return False

# Initialize sheet sync
sheet_sync = SheetSync()

# Configure scheduler
scheduler = AsyncIOScheduler(
    jobstores={'default': MemoryJobStore()},
    executors={'default': ThreadPoolExecutor(20)},
    timezone='UTC'
)

async def _sync_leads():
    logging.info("Starting leads sync")
    await google_sheets.upsert_leads_to_db()

async def _sync_tones():
    logging.info("Starting tones sync")
    await google_sheets.upsert_tones_to_db()

def start_scheduler():
    # Schedule leads sync at configured hour/minute
    scheduler.add_job(
        lambda: asyncio.create_task(_sync_leads()),
        "cron",
        hour=settings.SHEET_SYNC_HOUR,
        minute=settings.SHEET_SYNC_MINUTE,
        id="sheet_sync_leads"
    )
    # Schedule tones sync offset by 5 minutes
    scheduler.add_job(
        lambda: asyncio.create_task(_sync_tones()),
        "cron",
        hour=settings.SHEET_SYNC_HOUR,
        minute=(settings.SHEET_SYNC_MINUTE + 5) % 60,
        id="sheet_sync_tones"
    )
    scheduler.start()
    logging.info("Google Sheets sync scheduler started")

def stop_scheduler():
    """Stop the scheduler gracefully."""
    try:
        scheduler.shutdown()
        logger.info("Sheet sync scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        raise
