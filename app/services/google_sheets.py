import json
import logging
import time
from functools import lru_cache
from typing import List, Dict, Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.config_manager import get_settings, Settings
from app.services.supabase_client import supabase_client

settings: Settings = get_settings()
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

class GoogleSheetsService:
    def __init__(self):
        creds_info = json.loads(settings.GOOGLE_SHEETS_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        self.client = build("sheets", "v4", credentials=creds)
        self.sheet_id = settings.GOOGLE_SHEETS_ID
        # Ranges pulled from settings—no hard-coded strings here
        self.ranges = {
            "leads": f"{settings.LEADS_SHEET_NAME}!{settings.GOOGLE_SHEETS_LEADS_RANGE}",
            "tones": f"{settings.TONE_SETTINGS_SHEET_NAME}!{settings.GOOGLE_SHEETS_TONE_RANGE}",
        }

    def _normalize_headers(self, headers: List[str]) -> List[str]:
        return [h.strip().lower().replace(" ", "_") for h in headers]

    def _fetch_rows(self, name: str) -> List[List[Any]]:
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
        leads = await self.fetch_leads()
        start = time.time()
        success, failed = 0, 0
        for lead in leads:
            try:
                supabase_client.upsert_lead(lead)
                success += 1
            except Exception as e:
                logging.error("Upsert lead %s failed: %s", lead.get("id"), e)
                failed += 1
        logging.info("Leads upsert complete. Success: %d, Failed: %d, Time: %.2fs",
                     success, failed, time.time() - start)

    async def upsert_tones(self) -> None:
        tones = await self.fetch_tones()
        start = time.time()
        success, failed = 0, 0
        for broker_id, tone in tones.items():
            try:
                supabase_client.client.table("brokers").upsert({
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

@lru_cache()
def get_google_sheets_service() -> GoogleSheetsService:
    return GoogleSheetsService()
