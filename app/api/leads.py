from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
from app.api.dependencies import get_current_active_user, get_current_admin_user
from app.services.supabase_client import supabase
from app.models.priority import priority_scorer
from app.jobs.sheet_sync import sheet_sync

router = APIRouter(prefix="/leads", tags=["leads"])

class LeadBase(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    status: str = "New"
    notes: Optional[str] = None
    metadata: Optional[dict] = None

class LeadCreate(LeadBase):
    pass

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None

class Lead(LeadBase):
    id: str
    created_at: datetime
    updated_at: datetime
    priority_score: Optional[float] = None

    class Config:
        from_attributes = True

@router.get("/", response_model=List[Lead])
async def get_leads(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get a list of leads with optional filtering."""
    try:
        # Get leads from Supabase
        query = supabase.client.table("leads").select("*")

        if status:
            query = query.eq("status", status)

        result = query.range(skip, skip + limit - 1).execute()
        leads = result.data or []

        # Calculate priority scores
        for lead in leads:
            lead["priority_score"] = priority_scorer.calculate_priority_score(lead)

        return leads
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/priority", response_model=List[Lead])
async def get_priority_leads(
    batch_size: int = 10,
    current_user: dict = Depends(get_current_active_user)
):
    """Get a batch of leads sorted by priority score."""
    try:
        # Get all active leads
        result = supabase.client.table("leads").select("*").eq("status", "Active").execute()
        leads = result.data or []

        # Get priority batch
        priority_leads = priority_scorer.get_priority_batch(leads, batch_size)
        return priority_leads
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{lead_id}", response_model=Lead)
async def get_lead(
    lead_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get a specific lead by ID."""
    try:
        lead = supabase.get_lead_details(lead_id)
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found"
            )

        # Calculate priority score
        lead["priority_score"] = priority_scorer.calculate_priority_score(lead)
        return lead
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/", response_model=Lead, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead: LeadCreate,
    current_user: dict = Depends(get_current_admin_user)
):
    """Create a new lead."""
    try:
        # Insert into Supabase
        result = supabase.client.table("leads").insert(lead.dict()).execute()
        new_lead = result.data[0] if result.data else None

        if not new_lead:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create lead"
            )

        # Sync to Google Sheets if available
        if sheet_sync.worksheet:
            sheet_sync.update_lead_status(
                new_lead["id"],
                new_lead["status"],
                new_lead["notes"]
            )

        return new_lead
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.patch("/{lead_id}", response_model=Lead)
async def update_lead(
    lead_id: str,
    lead_update: LeadUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update a lead."""
    try:
        # Update in Supabase
        result = supabase.client.table("leads").update(
            lead_update.dict(exclude_unset=True)
        ).eq("id", lead_id).execute()

        updated_lead = result.data[0] if result.data else None
        if not updated_lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found"
            )

        # Sync to Google Sheets if available
        if sheet_sync.worksheet:
            sheet_sync.update_lead_status(
                updated_lead["id"],
                updated_lead["status"],
                updated_lead["notes"]
            )

        return updated_lead
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """Delete a lead."""
    try:
        # Delete from Supabase
        result = supabase.client.table("leads").delete().eq("id", lead_id).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
