#!/usr/bin/env python3
"""
analyze_sheets.py

Enterprise-grade ad-hoc analysis of your Google Sheets lead data.
– Loads leads via GoogleSheetsService
– Builds key metrics (total leads, brokers on, docs requested, follow-ups today)
– Exports to JSON or CSV
– Robust error handling, retries, structured logging
"""

import argparse
import csv
import json
import logging
from datetime import datetime
from typing import List, Dict

from app.config import settings
from app.models.lead import Lead
from app.services.google_sheets import GoogleSheetsService
from app.services.supabase_service import supabase_service
from app.utils.date_utils import format_date

# Structured logging
logger = logging.getLogger("lead_followup.analyze")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


def load_leads() -> List[Lead]:
    """Fetch all leads from Sheets and parse into Pydantic models."""
    sheets = GoogleSheetsService()
    raw_rows = sheets.get_all_leads()
    leads: List[Lead] = []
    for rec in raw_rows:
        try:
            lead = Lead(**rec)
            leads.append(lead)
        except Exception as ex:
            logger.warning(f"Skipping invalid row {rec.get('_row_number')}: {ex}")
    logger.info(f"Loaded {len(leads)} valid leads from sheet")
    return leads


def compute_stats(leads: List[Lead]) -> Dict[str, int]:
    """Compute top-level metrics and pull today's follow-up count from Supabase."""
    # Base metrics
    total = len(leads)
    brokers_on = sum(1 for l in leads if (l.broker_status or "").strip().lower() == "on")
    docs_req = sum(
        1 for l in leads
        if l.last_update and l.last_update.lower().startswith("requested docs")
    )

    # Idempotent follow-ups from Supabase
    today = format_date(datetime.utcnow())
    try:
        followed = supabase_service.get_today_followups(today)
        followup_count = len(followed)
    except Exception as ex:
        logger.error(f"Error fetching today's followups: {ex}")
        followup_count = -1  # signal error

    stats = {
        "total_leads": total,
        "brokers_on": brokers_on,
        "docs_requested": docs_req,
        "followups_today": followup_count,
    }
    logger.info(f"Computed stats: {stats}")
    return stats


def export_json(stats: Dict[str, int], path: str) -> None:
    """Write stats to a JSON file."""
    with open(path, "w") as f:
        json.dump(stats, f, indent=2)
    logger.info(f"JSON report written to {path}")


def export_csv(stats: Dict[str, int], path: str) -> None:
    """Write stats to a CSV file."""
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for key, val in stats.items():
            writer.writerow([key, val])
    logger.info(f"CSV report written to {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze lead follow-up Google Sheets and export metrics."
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output file path (e.g. stats.json or stats.csv)"
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "csv"],
        default="json",
        help="Export format"
    )
    args = parser.parse_args()

    leads = load_leads()
    stats = compute_stats(leads)

    if args.format == "json":
        export_json(stats, args.output)
    else:
        export_csv(stats, args.output)


if __name__ == "__main__":
    main()
