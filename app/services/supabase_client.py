from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from supabase import create_client, Client
from app.services.config_manager import get_settings
from pydantic import BaseModel
from functools import wraps
import time
import os
import asyncio

logger = logging.getLogger(__name__)

# Initialize settings
settings = get_settings()

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
                        await asyncio.sleep(sleep_time)

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
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self.initialize()

    def initialize(self):
        """Initialize the Supabase client."""
        try:
            # Remove proxy-related environment variables before initializing Supabase client
            for proxy_key in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
                os.environ.pop(proxy_key, None)

            # Initialize Supabase client
            self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            raise

    @property
    def client(self) -> Client:
        """Get the Supabase client instance."""
        if self._client is None:
            self.initialize()
        return self._client

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
            result = self.client.table("conversations").insert(data).execute()
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

            result = query.order("created_at", desc=True).limit(limit).execute()
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
            result = self.client.table("leads").update(data).eq("id", lead_id).execute()
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
            result = self.client.table("leads").select("*").eq("id", lead_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get lead details: {e}")
            return None

    @retry_on_failure(times=3, delay=0.5)
    async def fetch_leads(self) -> List[Dict[str, Any]]:
        """Fetch all active leads."""
        if not self.client:
            logger.warning("Supabase client not initialized")
            return []

        try:
            result = self.client.table("leads").select("*").eq("status", "active").execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to fetch leads: {e}")
            return []

    async def is_connected(self) -> bool:
        """Check if the Supabase connection is healthy."""
        try:
            # Try to execute a simple query
            self.client.table("leads").select("count", count="exact").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase health check failed: {str(e)}")
            return False

    @retry_on_failure(times=3, delay=0.5)
    async def get_queued_followups(self) -> List[Dict[str, Any]]:
        """Fetch all queued follow-ups."""
        if not self.client:
            logger.warning("Supabase client not initialized")
            return []

        try:
            result = self.client.table("followups").select("*").eq("status", "queued").execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to fetch queued follow-ups: {e}")
            return []

    @retry_on_failure(times=3, delay=0.5)
    async def mark_followup_sent(self, followup_id: str) -> Optional[Dict[str, Any]]:
        """Mark a follow-up as sent."""
        if not self.client:
            logger.warning("Supabase client not initialized")
            return None

        try:
            data = {
                "status": "sent",
                "sent_at": datetime.utcnow().isoformat()
            }
            result = self.client.table("followups").update(data).eq("id", followup_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to mark follow-up as sent: {e}")
            return None

# Defer client initialization
_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client

# Export the getter function instead of the instance
__all__ = ['get_supabase_client']
