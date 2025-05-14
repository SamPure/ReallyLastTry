from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from supabase import create_client, Client
from app.services.config_manager import settings
from pydantic import BaseModel
from functools import wraps
import time

logger = logging.getLogger(__name__)

def retry_on_failure(times: int = 3, delay: float = 1.0):
    """Decorator for retrying failed Supabase operations with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(times):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"Supabase call failed (attempt {attempt+1}/{times}): {str(e)}",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_attempts": times
                        }
                    )
                    if attempt < times - 1:  # Don't sleep on the last attempt
                        sleep_time = delay * (2 ** attempt)
                        logger.info(f"Retrying in {sleep_time:.2f} seconds...")
                        time.sleep(sleep_time)

            logger.error(
                f"Supabase call failed after {times} attempts",
                extra={
                    "function": func.__name__,
                    "error": str(last_error)
                }
            )
            raise RuntimeError(f"Supabase call failed after {times} attempts: {str(last_error)}")
        return wrapper
    return decorator

class SupabaseClient:
    def __init__(self):
        self.client: Optional[Client] = None
        if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
            try:
                self.client = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_SERVICE_KEY
                )
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.client = None

    @retry_on_failure(times=3, delay=0.5)
    async def insert_conversation(
        self,
        lead_id: str,
        message: str,
        direction: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Insert a new conversation record."""
        if not self.client:
            logger.warning("Supabase client not initialized")
            return None

        try:
            data = {
                "lead_id": lead_id,
                "message": message,
                "direction": direction,
                "status": status,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat()
            }
            result = await self.client.table("conversations").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to insert conversation: {e}")
            return None

    @retry_on_failure(times=3, delay=0.5)
    async def fetch_recent_conversations(
        self,
        lead_id: str,
        limit: int = 10,
        before_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch recent conversations for a lead."""
        if not self.client:
            logger.warning("Supabase client not initialized")
            return []

        try:
            query = self.client.table("conversations").select("*").eq("lead_id", lead_id)

            if before_date:
                query = query.lt("created_at", before_date.isoformat())

            result = await query.order("created_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to fetch conversations: {e}")
            return []

    @retry_on_failure(times=3, delay=0.5)
    async def update_lead_status(
        self,
        lead_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update lead status and metadata."""
        if not self.client:
            logger.warning("Supabase client not initialized")
            return None

        try:
            data = {
                "status": status,
                "metadata": metadata or {},
                "updated_at": datetime.utcnow().isoformat()
            }
            result = await self.client.table("leads").update(data).eq("id", lead_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to update lead status: {e}")
            return None

    @retry_on_failure(times=3, delay=0.5)
    async def get_lead_details(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a lead."""
        if not self.client:
            logger.warning("Supabase client not initialized")
            return None

        try:
            result = await self.client.table("leads").select("*").eq("id", lead_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get lead details: {e}")
            return None

# Initialize Supabase client
supabase = SupabaseClient()
