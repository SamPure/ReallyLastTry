import json
import logging
import time
from functools import lru_cache
from typing import List, Dict, Any, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.config_manager import get_settings, Settings
from app.services.supabase_client import get_supabase_client

settings: Settings = get_settings()
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

class GoogleSheetsService:
    def __init__(self):
        self.client = None
        self.sheet_id = None
        self.ranges = None

        # Check for empty credentials
        raw_json = settings.GOOGLE_SHEETS_CREDENTIALS_JSON.strip()
        if not raw_json:
            logger.warning("⚠️ Google Sheets credentials not configured. Skipping Sheets service.")
            return

        try:
            creds_info = json.loads(raw_json)
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            self.client = build("sheets", "v4", credentials=creds)
            self.sheet_id = settings.SHEET_ID
            # Ranges pulled from settings—no hard-coded strings here
            self.ranges = {
                "leads": f"{settings.LEADS_SHEET_NAME}!{settings.GOOGLE_SHEETS_LEADS_RANGE}",
                "tones": f"{settings.TONE_SETTINGS_SHEET_NAME}!{settings.GOOGLE_SHEETS_TONE_RANGE}",
            }
            logger.info("Google Sheets service initialized successfully")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid Google Sheets credentials JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {e}")

    def _normalize_headers(self, headers: List[str]) -> List[str]:
        return [h.strip().lower().replace(" ", "_") for h in headers]

    def _fetch_rows(self, name: str) -> List[List[Any]]:
        if not self.client:
            logger.warning("Google Sheets client not initialized. Skipping fetch.")
            return []

        try:
            resp = (
                self.client.spreadsheets()
                    .values()
                    .get(spreadsheetId=self.sheet_id, range=self.ranges[name])
                    .execute()
            )
            return resp.get("values", [])
        except HttpError as e:
            logging.error("Google API error fetching %s: %s", name, e)
            return []

    async def fetch_leads(self) -> List[Dict[str, Any]]:
        if not self.client:
            logger.warning("Google Sheets client not initialized. Skipping leads fetch.")
            return []

        rows = self._fetch_rows("leads")
        if not rows or len(rows) < 2:
            return []
        headers = self._normalize_headers(rows[0])
        leads: List[Dict[str, Any]] = []
        for row in rows[1:]:
            data = dict(zip(headers, row))
            leads.append({
                "id": data.get("lead_id", ""),
                "name": data.get("name", ""),
                "phone": data.get("phone", ""),
                "email": data.get("email", ""),
                "status": data.get("status", ""),
                # collect any extra columns into metadata
                "metadata": {k: v for k, v in data.items() if k not in {"lead_id","name","phone","email","status"}}
            })
        return leads

    async def fetch_tones(self) -> Dict[str, Dict[str, Any]]:
        if not self.client:
            logger.warning("Google Sheets client not initialized. Skipping tones fetch.")
            return {}

        rows = self._fetch_rows("tones")
        if not rows or len(rows) < 2:
            return {}
        headers = self._normalize_headers(rows[0])
        tones: Dict[str, Dict[str, Any]] = {}
        for row in rows[1:]:
            data = dict(zip(headers, row))
            broker_id = data.get("broker_id")
            if not broker_id:
                logging.warning("Skipping tone row without broker_id: %s", row)
                continue
            examples = (data.get("examples") or "")
            tones[broker_id] = {
                "tone_style": data.get("tone_style", ""),
                "examples": [ex.strip() for ex in examples.split(";") if ex.strip()],
            }
        return tones

    async def upsert_leads(self) -> None:
        if not self.client:
            logger.warning("Google Sheets client not initialized. Skipping leads upsert.")
            return

        leads = await self.fetch_leads()
        start = time.time()
        success, failed = 0, 0
        for lead in leads:
            try:
                get_supabase_client().upsert_lead(lead)
                success += 1
            except Exception as e:
                logging.error("Upsert lead %s failed: %s", lead.get("id"), e)
                failed += 1
        logging.info("Leads upsert complete. Success: %d, Failed: %d, Time: %.2fs",
                     success, failed, time.time() - start)

    async def upsert_tones(self) -> None:
        if not self.client:
            logger.warning("Google Sheets client not initialized. Skipping tones upsert.")
            return

        tones = await self.fetch_tones()
        start = time.time()
        success, failed = 0, 0
        for broker_id, tone in tones.items():
            try:
                get_supabase_client().client.table("brokers").upsert({
                    "id": broker_id,
                    "tone_style": tone["tone_style"],
                    "examples": tone["examples"],
                }).execute()
                success += 1
            except Exception as e:
                logging.error("Upsert tone %s failed: %s", broker_id, e)
                failed += 1
        logging.info("Tones upsert complete. Success: %d, Failed: %d, Time: %.2fs",
                     success, failed, time.time() - start)

    def is_healthy(self) -> bool:
        """Check if the Google Sheets service is healthy."""
        if not self.client:
            return True  # Consider it healthy if not configured
        try:
            # Try a simple API call to verify credentials
            self.client.spreadsheets().get(spreadsheetId=self.sheet_id).execute()
            return True
        except Exception as e:
            logger.error(f"Google Sheets health check failed: {e}")
            return False

@lru_cache()
def get_google_sheets_service() -> GoogleSheetsService:
    return GoogleSheetsService()
