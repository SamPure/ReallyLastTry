import pytest
from unittest.mock import Mock, patch
from app.services.batch_processor import BatchProcessor

@pytest.fixture
def mock_redis():
    with patch('app.utils.redis_utils.get_redis') as mock:
        yield mock

@pytest.fixture
def mock_sheets():
    with patch('app.services.google_sheets.GoogleSheetsService') as mock:
        yield mock

def test_batch_processor_enqueue(mock_redis):
    processor = BatchProcessor()
    processor.enqueue_update(1, "Last Texted", "2024-03-20")
    mock_redis.return_value.rpush.assert_called_once_with(
        "sheets_batch", "1|Last Texted|2024-03-20"
    )

def test_batch_processor_process_empty(mock_redis, mock_sheets):
    mock_redis.return_value.lpop.return_value = None
    processor = BatchProcessor()
    processor.process_batch()
    mock_sheets.return_value.leads_ws.update_cells.assert_not_called()

def test_batch_processor_process_chunks(mock_redis, mock_sheets):
    mock_redis.return_value.lpop.side_effect = [
        "1|Last Texted|2024-03-20",
        "2|Last Texted|2024-03-20",
        None
    ]
    processor = BatchProcessor(chunk_size=1)
    processor.process_batch()
    assert mock_sheets.return_value.leads_ws.update_cells.call_count == 2
