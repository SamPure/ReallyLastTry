import logging
import httpx
from app.services.config_manager import settings

logger = logging.getLogger("lead_followup.kixie_service")


class SMSService:
    def __init__(self):
        self.client = httpx.Client(
            base_url=settings.KIXIE_BASE_URL,
            headers={"Authorization": f"Bearer {settings.KIXIE_API_KEY}"},
        )

    def send_sms(self, to: str, body: str) -> None:
        try:
            response = self.client.post(
                "/v1/send",
                json={
                    "to": to,
                    "business_id": settings.KIXIE_BUSINESS_ID,
                    "message": body,
                },
            )
            response.raise_for_status()
            logger.info(f"SMS sent to {to}")
        except Exception as e:
            logger.error(f"SMS send failed: {e}")
            raise
