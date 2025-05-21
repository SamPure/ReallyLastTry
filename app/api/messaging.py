from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from datetime import datetime
from app.api.dependencies import get_current_active_user, get_current_admin_user
from app.services.kixie_handler import kixie_handler
from app.services.email_service import email_service
from app.services.supabase_client import get_supabase_client
from app.jobs.scheduler_service import run_followups

router = APIRouter(prefix="/messaging", tags=["messaging"])

class SMSMessage(BaseModel):
    phone: str
    message: str
    lead_id: Optional[str] = None

class EmailMessage(BaseModel):
    to_email: EmailStr
    subject: str
    template_name: str
    template_data: dict
    lead_id: Optional[str] = None

class WebhookData(BaseModel):
    type: str
    data: dict

@router.post("/sms", status_code=status.HTTP_200_OK)
async def send_sms(
    message: SMSMessage,
    current_user: dict = Depends(get_current_active_user)
):
    """Send an SMS message."""
    try:
        # Send SMS via Kixie
        response = await kixie_handler.send_sms(
            message.phone,
            message.message,
            message.lead_id
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/email", status_code=status.HTTP_200_OK)
async def send_email(
    email: EmailMessage,
    current_user: dict = Depends(get_current_active_user)
):
    """Send an email using a template."""
    try:
        # Send email
        response = await email_service.send_email(
            to_email=email.to_email,
            subject=email.subject,
            template_name=email.template_name,
            template_data=email.template_data,
            lead_id=email.lead_id
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/kixie/webhook", status_code=status.HTTP_200_OK)
async def kixie_webhook(
    request: Request,
    webhook_data: WebhookData
):
    """Handle incoming Kixie webhooks."""
    try:
        # Process webhook
        response = await kixie_handler.handle_webhook(webhook_data.data)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/conversations/{lead_id}", status_code=status.HTTP_200_OK)
async def get_conversations(
    lead_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all conversations for a lead."""
    try:
        # Get conversations from Supabase
        result = get_supabase_client().client.table("conversations").select("*").eq("lead_id", lead_id).execute()
        conversations = result.data or []
        return conversations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/daily-report", status_code=status.HTTP_200_OK)
async def send_daily_report(
    current_user: dict = Depends(get_current_admin_user)
):
    """Send daily report to configured recipients."""
    try:
        # Send daily report
        response = await email_service.send_daily_report()
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/followups/trigger", status_code=status.HTTP_200_OK)
async def trigger_followups(
    current_user: dict = Depends(get_current_admin_user)
):
    """Manually trigger the follow-up process."""
    try:
        # Run follow-ups
        await run_followups()
        return {"status": "success", "message": "Follow-ups triggered successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
