from datetime import datetime
from typing import Optional

def format_date(dt: Optional[datetime] = None) -> str:
    """
    Format a datetime as YYYY-MM-DD.
    If no datetime is provided, uses current time.
    """
    if dt is None:
        dt = datetime.utcnow()
    return dt.strftime("%Y-%m-%d")

def parse_date(date_str: str) -> datetime:
    """
    Parse a YYYY-MM-DD string into a datetime.
    Raises ValueError if the string is not in the correct format.
    """
    return datetime.strptime(date_str, "%Y-%m-%d")
