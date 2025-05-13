import logging
import time
import random
from datetime import datetime
from prometheus_client import Counter
from app.config import settings
from app.core.decorators import with_retry

logger = logging.getLogger("lead_followup.supabase_service")
supabase_errors = Counter("supabase_errors_total", "Supabase operation failures")
supabase = settings.supabase_client


class SupabaseService:
    @with_retry(error_counter=supabase_errors)
    def has_followup(self, row_number: int, date_str: str) -> bool:
        resp = (
            supabase.table("followup_logs")
            .select("id")
            .eq("sheet_row", row_number)
            .eq("date", date_str)
            .execute()
        )
        return bool(resp.data)

    @with_retry(error_counter=supabase_errors)
    def log_followup(
        self, row_number: int, action: str, date_str: str, first_name: str, company: str
    ):
        supabase.table("followup_logs").insert(
            {
                "sheet_row": row_number,
                "action": action,
                "date": date_str,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {"first_name": first_name, "company": company},
            }
        ).execute()

    @with_retry(error_counter=supabase_errors)
    def get_today_followups(self, date_str: str) -> list:
        resp = (
            supabase.table("followup_logs")
            .select("metadata")
            .eq("date", date_str)
            .execute()
        )
        return [
            f"{r['metadata']['first_name']} ({r['metadata']['company']})"
            for r in resp.data
        ]


supabase_service = SupabaseService()
