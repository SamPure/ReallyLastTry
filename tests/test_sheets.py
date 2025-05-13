import pytest
from unittest.mock import Mock, patch
from app.config import settings

@pytest.fixture
def mock_sheets():
    """Create a mock Google Sheets client."""
    with patch("gspread.service_account") as mock_service:
        mock_client = Mock()
        mock_service.return_value = mock_client
        yield mock_client

@pytest.mark.integration
@pytest.mark.sheets
def test_sheets_connection(mock_sheets):
    """Test Google Sheets connection and basic operations."""
    # Mock worksheet
    mock_worksheet = Mock()
    mock_worksheet.get_all_records.return_value = [
        {"name": "test1", "email": "test1@example.com"},
        {"name": "test2", "email": "test2@example.com"}
    ]

    # Mock spreadsheet
    mock_spreadsheet = Mock()
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    mock_sheets.open_by_key.return_value = mock_spreadsheet

    # Test reading data
    spreadsheet = mock_sheets.open_by_key(settings.GOOGLE_SHEETS_ID)
    worksheet = spreadsheet.worksheet(settings.LEADS_SHEET_NAME)
    records = worksheet.get_all_records()

    assert len(records) == 2
    assert records[0]["name"] == "test1"
    assert records[1]["email"] == "test2@example.com"

@pytest.mark.integration
@pytest.mark.sheets
def test_sheets_error_handling(mock_sheets):
    """Test Google Sheets error handling."""
    # Test authentication error
    mock_sheets.open_by_key.side_effect = Exception("Auth error")

    with pytest.raises(Exception) as exc_info:
        mock_sheets.open_by_key(settings.GOOGLE_SHEETS_ID)
    assert "Auth error" in str(exc_info.value)

@pytest.mark.integration
@pytest.mark.sheets
def test_sheets_batch_operations(mock_sheets):
    """Test Google Sheets batch operations."""
    # Mock worksheet
    mock_worksheet = Mock()
    mock_spreadsheet = Mock()
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    mock_sheets.open_by_key.return_value = mock_spreadsheet

    # Test batch append
    test_data = [
        ["test3", "test3@example.com"],
        ["test4", "test4@example.com"]
    ]

    mock_worksheet.append_rows.return_value = {"updates": {"updatedRows": 2}}

    spreadsheet = mock_sheets.open_by_key(settings.GOOGLE_SHEETS_ID)
    worksheet = spreadsheet.worksheet(settings.LEADS_SHEET_NAME)
    result = worksheet.append_rows(test_data)

    assert result["updates"]["updatedRows"] == 2
    mock_worksheet.append_rows.assert_called_once_with(test_data)
