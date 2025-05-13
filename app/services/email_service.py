import logging
import httpx
from app.config import settings

logger = logging.getLogger("lead_followup.email_service")

class EmailService:
    def __init__(self):
        self.client = httpx.Client(
            base_url="https://api.email-provider.com",  # Replace with your provider
            headers={"Authorization": f"Bearer {settings.EMAIL_API_KEY}"}
        )

    def send_email(self, to: str, subject: str, body: str) -> None:
        try:
            response = self.client.post(
                "/v1/send",
                json={
                    "to": to,
                    "from": settings.EMAIL_SENDER,
                    "subject": subject,
                    "text": body
                }
            )
            response.raise_for_status()
            logger.info(f"Email sent to {to}: {subject}")
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            raise

    def send_daily_report(self, date_str: str, summary_list: list) -> None:
        subject = f"Daily Lead Follow-up Report – {date_str}"
        body = "Leads followed up today:\n" + "\n".join(summary_list)
        self.send_email(settings.EMAIL_DAILY_REPORT_TO, subject, body)
