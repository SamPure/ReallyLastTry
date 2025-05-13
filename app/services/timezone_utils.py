from datetime import datetime
import pytz
from app.config import settings


def get_timezone_from_area_code(area_code: str) -> str:
    area_code = (area_code or "").strip()
    if not area_code:
        return "UTC"

    # Add more mappings as needed
    timezone_map = {
        "212": "America/New_York",
        "415": "America/Los_Angeles",
        "312": "America/Chicago",
        # Add more mappings
    }
    return timezone_map.get(area_code, "UTC")


def now_in_timezone(area_code: str) -> datetime:
    tz = get_timezone_from_area_code(area_code)
    return datetime.now(pytz.timezone(tz))
