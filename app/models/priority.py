from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from functools import lru_cache
from app.services.config_manager import get_settings, Settings
from app.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

settings: Settings = get_settings()

@lru_cache()
def get_weights() -> Dict[str, float]:
    return {
        "recency": settings.PRIORITY_RECENCY_WEIGHT,         # e.g. 0.5
        "engagement": settings.PRIORITY_ENGAGEMENT_WEIGHT,   # e.g. 0.3
        "classification": settings.PRIORITY_CLASS_WEIGHT,    # e.g. 0.2
    }

class PriorityScorer:
    def __init__(self):
        self.weights = get_weights()

    def _recency_score(self, last_contact: datetime) -> float:
        # more recent = higher score
        days = (datetime.utcnow() - last_contact).days
        # exponential decay
        return max(0.0, 1.0 - (days / settings.PRIORITY_RECENCY_HALF_LIFE_DAYS))

    def _engagement_score(self, lead_id: str) -> float:
        # ratio of inbound to total messages in window
        window = datetime.utcnow() - timedelta(days=settings.PRIORITY_ENGAGEMENT_WINDOW_DAYS)
        convs = get_supabase_client().fetch_recent_conversations(lead_id, limit=1000)
        inbound = sum(1 for m in convs if m["role"] == "inbound" and m["timestamp"] >= window.isoformat())
        total   = sum(1 for m in convs if m["timestamp"] >= window.isoformat())
        return (inbound / total) if total else 0.0

    def _classification_score(self, lead: Dict[str, Any]) -> float:
        # Simple mapping of lead.metadata['classification']
        cls = lead.get("metadata", {}).get("classification", "").lower()
        return settings.PRIORITY_CLASS_SCORES.get(cls, settings.PRIORITY_CLASS_SCORES["default"])

    def compute(self, lead: Dict[str, Any]) -> float:
        # Fetch last contact timestamp
        recent = get_supabase_client().fetch_recent_conversations(lead["id"], limit=1)
        if recent:
            last_ts = datetime.fromisoformat(recent[0]["timestamp"])
        else:
            # never contacted = highest recency urgency
            last_ts = datetime.utcnow() - timedelta(days=settings.PRIORITY_RECENCY_HALF_LIFE_DAYS)
        r = self._recency_score(last_ts)
        e = self._engagement_score(lead["id"])
        c = self._classification_score(lead)

        score = (
            r * self.weights["recency"]
            + e * self.weights["engagement"]
            + c * self.weights["classification"]
        )
        return round(score, 4)

    def calculate_priority_score(self, lead: Dict[str, Any]) -> float:
        """Calculate priority score for a lead based on various factors."""
        try:
            score = 0.0

            # Response time score (0-1)
            response_time = self._get_response_time_score(lead)
            score += response_time * self.weights["response_time"]

            # Lead source score (0-1)
            source_score = self._get_source_score(lead)
            score += source_score * self.weights["lead_source"]

            # Interaction frequency score (0-1)
            interaction_score = self._get_interaction_score(lead)
            score += interaction_score * self.weights["interaction_frequency"]

            # Lead value score (0-1)
            value_score = self._get_value_score(lead)
            score += value_score * self.weights["lead_value"]

            # Time since last contact score (0-1)
            time_score = self._get_time_score(lead)
            score += time_score * self.weights["time_since_last_contact"]

            return min(max(score, 0.0), 1.0)  # Normalize to 0-1
        except Exception as e:
            logger.error(f"Error calculating priority score: {e}")
            return 0.5  # Default to medium priority

    def _get_response_time_score(self, lead: Dict[str, Any]) -> float:
        """Calculate score based on lead's response time."""
        try:
            last_response = lead.get("last_response_time")
            if not last_response:
                return 0.5  # Default score if no response time

            response_time = datetime.fromisoformat(last_response)
            time_diff = datetime.now() - response_time

            # Score decreases as time since last response increases
            if time_diff < timedelta(hours=1):
                return 1.0
            elif time_diff < timedelta(hours=24):
                return 0.8
            elif time_diff < timedelta(days=3):
                return 0.6
            elif time_diff < timedelta(days=7):
                return 0.4
            else:
                return 0.2
        except Exception as e:
            logger.error(f"Error calculating response time score: {e}")
            return 0.5

    def _get_source_score(self, lead: Dict[str, Any]) -> float:
        """Calculate score based on lead source."""
        source = lead.get("metadata", {}).get("source", "").lower()

        # Define source weights
        source_weights = {
            "referral": 1.0,
            "website": 0.9,
            "social": 0.8,
            "email": 0.7,
            "phone": 0.6,
            "other": 0.5
        }

        return source_weights.get(source, 0.5)

    def _get_interaction_score(self, lead: Dict[str, Any]) -> float:
        """Calculate score based on interaction frequency."""
        try:
            if not get_supabase_client():
                return 0.5

            # Get conversation count from Supabase
            conversations = get_supabase_client().fetch_recent_conversations(
                lead_id=lead["id"],
                limit=100  # Get last 100 conversations
            )

            # Score based on number of interactions
            count = len(conversations)
            if count > 10:
                return 1.0
            elif count > 5:
                return 0.8
            elif count > 2:
                return 0.6
            elif count > 0:
                return 0.4
            else:
                return 0.2
        except Exception as e:
            logger.error(f"Error calculating interaction score: {e}")
            return 0.5

    def _get_value_score(self, lead: Dict[str, Any]) -> float:
        """Calculate score based on lead value indicators."""
        try:
            metadata = lead.get("metadata", {})

            # Check for high-value indicators
            if metadata.get("priority") == "High":
                return 1.0
            elif metadata.get("priority") == "Medium":
                return 0.7
            elif metadata.get("priority") == "Low":
                return 0.4

            # Check for other value indicators
            value_indicators = [
                metadata.get("budget", 0),
                metadata.get("property_value", 0),
                metadata.get("urgency", 0)
            ]

            # Calculate average of indicators
            avg_value = sum(value_indicators) / len(value_indicators)
            return min(max(avg_value / 100, 0.0), 1.0)  # Normalize to 0-1
        except Exception as e:
            logger.error(f"Error calculating value score: {e}")
            return 0.5

    def _get_time_score(self, lead: Dict[str, Any]) -> float:
        """Calculate score based on time since last contact."""
        try:
            last_contact = lead.get("last_contact")
            if not last_contact:
                return 1.0  # High priority if never contacted

            contact_time = datetime.fromisoformat(last_contact)
            time_diff = datetime.now() - contact_time

            # Score increases as time since last contact increases
            if time_diff < timedelta(hours=24):
                return 0.2
            elif time_diff < timedelta(days=3):
                return 0.4
            elif time_diff < timedelta(days=7):
                return 0.6
            elif time_diff < timedelta(days=14):
                return 0.8
            else:
                return 1.0
        except Exception as e:
            logger.error(f"Error calculating time score: {e}")
            return 0.5

    def get_priority_batch(
        self,
        leads: List[Dict[str, Any]],
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """Get a batch of leads sorted by priority score."""
        try:
            # Calculate scores for all leads
            scored_leads = [
                {**lead, "priority_score": self.calculate_priority_score(lead)}
                for lead in leads
            ]

            # Sort by priority score (descending)
            sorted_leads = sorted(
                scored_leads,
                key=lambda x: x["priority_score"],
                reverse=True
            )

            # Return top N leads
            return sorted_leads[:batch_size]
        except Exception as e:
            logger.error(f"Error getting priority batch: {e}")
            return leads[:batch_size]  # Return first N leads if error

# Initialize priority scorer
priority_scorer = PriorityScorer()
