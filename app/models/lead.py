from pydantic import BaseModel, Field
from typing import Optional


class Lead(BaseModel):
    row_number: int
    first_name: str = Field(..., alias="First Name")
    phone_number: str = Field(..., alias="Phone Number")
    area_code: str = Field(default="", alias="Area Code")
    company: Optional[str] = Field(default=None, alias="Company")
    email: Optional[str] = Field(default=None, alias="Email")
    last_texted: Optional[str] = Field(default=None, alias="Last Texted")
    status_update: Optional[str] = Field(default=None, alias="Status Update")
    ai_summary: Optional[str] = Field(default=None, alias="AI SUMMARY")
    broker_status: Optional[str] = Field(default=None, alias="Broker Status")
