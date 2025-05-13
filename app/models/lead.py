from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Lead(BaseModel):
    """Model for a lead from Google Sheets."""
    id: str = Field(..., description="Unique identifier for the lead")
    name: str = Field(..., description="Lead's full name")
    email: str = Field(..., description="Lead's email address")
    phone: str = Field(..., description="Lead's phone number")
    created_at: datetime = Field(..., description="When the lead was created")
    last_contacted: Optional[datetime] = Field(None, description="Last follow-up attempt")
    status: str = Field(..., description="Current lead status")
    notes: Optional[str] = Field(None, description="Additional notes about the lead")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
