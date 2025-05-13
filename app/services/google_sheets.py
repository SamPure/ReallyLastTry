from typing import List, Optional
import gspread
from app.core.decorators import with_retry
from app.models.lead import Lead

class GoogleSheetsService:
    def __init__(self, credentials: dict, spreadsheet_id: str):
        self.client = gspread.service_account_from_dict(credentials)
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)
        self.worksheet = self.spreadsheet.get_worksheet(0)  # First sheet

    @with_retry(max_retries=3)
    def get_all_leads(self) -> List[Lead]:
        """
        Fetch all leads from the Google Sheet.
        Returns a list of Lead objects.
        """
        records = self.worksheet.get_all_records()
        return [Lead(**record) for record in records]

    @with_retry(max_retries=3)
    def update_lead(self, lead: Lead) -> None:
        """
        Update a lead's information in the sheet.
        """
        # Find the row with matching ID
        cell = self.worksheet.find(lead.id)
        if cell:
            # Update the row
            row = [
                lead.id,
                lead.name,
                lead.email,
                lead.phone,
                lead.created_at.isoformat(),
                lead.last_contacted.isoformat() if lead.last_contacted else "",
                lead.status,
                lead.notes or ""
            ]
            self.worksheet.update(f"A{cell.row}:H{cell.row}", [row])
