import logging
import openai
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from app.services.config_manager import get_settings
from app.services.supabase_client import supabase_client
from app.services.kixie_handler import send_sms
from app.services.email_service import send_email
from app.models.priority import priority_scorer

settings = get_settings()
openai.api_key = settings.OPENAI_API_KEY

logger = logging.getLogger(__name__)

async def _fetch_context(lead_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch and format conversation history for the AI model."""
    try:
        rows = await supabase_client.fetch_recent_conversations(lead_id, limit=limit)
        # Format for ChatCompletion, preserving order
        return [
            {"role": row["role"], "content": row["message"]}
            for row in reversed(rows)
        ]
    except Exception as e:
        logger.error(f"Failed to fetch context for lead {lead_id}: {e}")
        return []

def _build_system_prompt(broker: Dict[str, Any]) -> str:
    """Build the system prompt with broker's tone and examples."""
    try:
        tone = broker.get("tone_style", "professional")
        examples = broker.get("examples", [])

        # Base prompt with tone and examples
        prompt = f"""
You are a broker at Pure Financial Funding.
Use a {tone} tone in every message.
Here are examples of how you sound:
{chr(10).join(f"- {ex}" for ex in examples)}

Guidelines:
- Keep messages concise and focused
- Maintain a natural, conversational tone
- Avoid using hyphens, dashes, or emojis
- Never use the phrase "follow up"
- Be strategic and value-focused
- Personalize based on the lead's context
"""
        return prompt.strip()
    except Exception as e:
        logger.error(f"Failed to build system prompt: {e}")
        return "You are a professional broker at Pure Financial Funding. Keep messages concise and natural."

async def _generate_ai_response(
    messages: List[Dict[str, str]],
    temperature: float = 0.7
) -> Tuple[Optional[str], Optional[str]]:
    """Generate AI response with error handling."""
    try:
        resp = openai.ChatCompletion.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=150,
        )
        return resp.choices[0].message.content.strip(), None
    except Exception as e:
        error_msg = f"OpenAI request failed: {str(e)}"
        logger.error(error_msg)
        return None, error_msg

async def _send_message(
    lead: Dict[str, Any],
    message: str
) -> Tuple[bool, Optional[str]]:
    """Send message via SMS with email fallback."""
    # Try SMS first
    try:
        await send_sms(lead["phone"], message)
        return True, None
    except Exception as sms_err:
        error_msg = f"SMS send failed: {str(sms_err)}"
        logger.warning(error_msg)

        # Fall back to email if enabled
        if settings.FALLBACK_EMAIL_ENABLED and lead.get("email"):
            try:
                await send_email(
                    to=lead["email"],
                    subject="Quick note from Pure Financial Funding",
                    body=message
                )
                return True, None
            except Exception as email_err:
                error_msg = f"Email fallback failed: {str(email_err)}"
                logger.error(error_msg)
                return False, error_msg
        return False, error_msg

async def generate_and_send_message(lead_id: str, score: float) -> None:
    """Generate and send an AI-powered message to a lead."""
    try:
        # 1. Load lead and broker info
        lead = await supabase_client.fetch_lead(lead_id)
        if not lead:
            logger.error(f"Lead {lead_id} not found")
            return

        broker = None
        if lead.get("assigned_broker_id"):
            try:
                broker = supabase_client.client.table("brokers")\
                    .select("*")\
                    .eq("id", lead["assigned_broker_id"])\
                    .single()\
                    .execute()\
                    .data
            except Exception as e:
                logger.warning(f"Failed to fetch broker for lead {lead_id}: {e}")

        # 2. Fetch conversation context
        history = await _fetch_context(lead_id)

        # 3. Build messages for OpenAI
        system_prompt = _build_system_prompt(broker or {})
        user_prompt = f"Score: {score}. Continue the conversation with {lead['name']}."
        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_prompt}
        ]

        # 4. Generate AI response
        ai_text, error = await _generate_ai_response(messages)
        if not ai_text:
            logger.error(f"Failed to generate message for lead {lead_id}: {error}")
            return

        # 5. Log the message
        try:
            await supabase_client.insert_conversation(
                lead_id=lead_id,
                role="outbound",
                message=ai_text,
                metadata={
                    "ai_generated": True,
                    "priority_score": score,
                    "broker_id": lead.get("assigned_broker_id")
                }
            )
        except Exception as e:
            logger.error(f"Failed to log AI message for lead {lead_id}: {e}")

        # 6. Send the message
        sent, error = await _send_message(lead, ai_text)
        if not sent:
            logger.error(f"Failed to send message to lead {lead_id}: {error}")
            return

        logger.info(
            "Message sent to lead %s (score=%.2f, broker=%s)",
            lead_id,
            score,
            lead.get("assigned_broker_id")
        )

    except Exception as e:
        logger.error(f"Unexpected error in generate_and_send_message for lead {lead_id}: {e}")
        raise
