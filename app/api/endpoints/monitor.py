from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from datetime import datetime

from app.services.email_service import email_service
from app.core.auth import get_current_admin_user

router = APIRouter()

@router.get("/email-queue/status", response_model=Dict[str, Any])
async def get_email_queue_status(
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Get current status of email queues and metrics.
    Requires admin authentication.

    Returns:
        Dict containing:
        - metrics: Email sending statistics
        - queue_size: Number of emails in main queue
        - retry_queue_size: Number of emails in retry queue
        - next_retry_time: When next retry batch will run
        - is_business_hours: Whether currently in business hours
    """
    try:
        status = email_service.get_queue_status()

        # Add timestamp and user info
        status.update({
            "timestamp": datetime.now().isoformat(),
            "monitored_by": current_user.get("email", "unknown")
        })

        return status
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get email queue status: {str(e)}"
        )

@router.get("/email-queue/health", response_model=Dict[str, Any])
async def get_email_health(
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Get health status of email service.
    Requires admin authentication.

    Returns:
        Dict containing:
        - status: "healthy" or "degraded"
        - last_success: Timestamp of last successful send
        - last_error: Timestamp and message of last error
        - queue_health: Status of main and retry queues
    """
    try:
        metrics = email_service.metrics.to_dict()

        # Determine overall health
        is_healthy = (
            metrics["total_failed"] < metrics["total_sent"] * 0.1  # Less than 10% failure rate
            and metrics["current_queue_size"] < 1000  # Queue not too large
            and metrics["current_retry_size"] < 100  # Retry queue not too large
        )

        # Calculate time since last success/error
        now = datetime.now()
        last_success = datetime.fromisoformat(metrics["last_success_time"]) if metrics["last_success_time"] else None
        last_error = datetime.fromisoformat(metrics["last_error_time"]) if metrics["last_error_time"] else None

        time_since_success = (now - last_success).total_seconds() if last_success else float('inf')
        time_since_error = (now - last_error).total_seconds() if last_error else float('inf')

        return {
            "status": "healthy" if is_healthy else "degraded",
            "last_success": {
                "timestamp": metrics["last_success_time"],
                "seconds_ago": time_since_success
            },
            "last_error": {
                "timestamp": metrics["last_error_time"],
                "message": metrics["last_error_message"],
                "seconds_ago": time_since_error
            },
            "queue_health": {
                "main_queue": {
                    "size": metrics["current_queue_size"],
                    "status": "ok" if metrics["current_queue_size"] < 1000 else "warning"
                },
                "retry_queue": {
                    "size": metrics["current_retry_size"],
                    "status": "ok" if metrics["current_retry_size"] < 100 else "warning"
                }
            },
            "metrics": {
                "total_sent": metrics["total_sent"],
                "total_failed": metrics["total_failed"],
                "total_retried": metrics["total_retried"],
                "failure_rate": metrics["total_failed"] / (metrics["total_sent"] + 1)  # Avoid division by zero
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get email health status: {str(e)}"
        )
