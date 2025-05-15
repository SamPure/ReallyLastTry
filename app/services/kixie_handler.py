from typing import Optional, Dict, Any
import logging
import httpx
from app.services.config_manager import settings
from app.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class KixieHandler:
    def __init__(self):
        self.base_url = settings.KIXIE_BASE_URL
        self.api_key = settings.KIXIE_API_KEY
        self.secret = settings.KIXIE_SECRET
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        self.supabase_client = get_supabase_client()

    async def send_sms(
        self,
        to_number: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Send an SMS message via Kixie."""
        if not self.api_key or not self.secret:
            logger.warning("Kixie credentials not configured")
            return None

        try:
            payload = {
                "to": to_number,
                "message": message,
                "metadata": metadata or {}
            }

            response = await self.client.post("/messages", json=payload)
            response.raise_for_status()

            result = response.json()

            # Log to Supabase if available
            if metadata and "lead_id" in metadata:
                await self.supabase_client.insert_conversation(
                    lead_id=metadata["lead_id"],
                    message=message,
                    direction="outbound",
                    status="sent",
                    metadata={"kixie_message_id": result.get("id")}
                )

            return result
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return None

    async def handle_webhook(self, payload: Dict[str, Any]) -> bool:
        """Handle incoming webhook from Kixie."""
        try:
            message_id = payload.get("id")
            from_number = payload.get("from")
            message = payload.get("message")
            status = payload.get("status")

            # Find lead by phone number in Supabase
            # This would need a new method in SupabaseClient to find by phone
            lead = await self.supabase_client.find_lead_by_phone(from_number)
            if lead:
                await self.supabase_client.insert_conversation(
                    lead_id=lead["id"],
                    message=message,
                    direction="inbound",
                    status=status,
                    metadata={"kixie_message_id": message_id}
                )
                return True

            return False
        except Exception as e:
            logger.error(f"Failed to handle Kixie webhook: {e}")
            return False

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

# Initialize Kixie handler
kixie_handler = KixieHandler()
