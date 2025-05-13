import logging
import time
from typing import List, Optional
from prometheus_client import Counter, Histogram
from app.config import settings
from app.core.constants import SHEETS_BATCH_KEY, DEFAULT_CHUNK_SIZE
from app.core.decorators import with_retry
from app.utils.redis_utils import get_redis
from app.services.google_sheets import GoogleSheetsService

logger = logging.getLogger("lead_followup.batch_processor")

# Metrics
batch_size = Histogram(
    "sheets_batch_size",
    "Number of cells in each batch update",
    buckets=[10, 50, 100, 500, 1000],
)
batch_duration = Histogram(
    "sheets_batch_duration_seconds",
    "Time taken to process each batch",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
)
redis_errors = Counter("redis_errors_total", "Redis operation failures")
sheets_errors = Counter("sheets_errors_total", "Sheets operation failures")


class BatchProcessor:
    def __init__(self, chunk_size: Optional[int] = None):
        self.chunk_size = chunk_size or DEFAULT_CHUNK_SIZE
        self.sheets = GoogleSheetsService()
        self.redis = get_redis()

    @with_retry(error_counter=redis_errors)
    def enqueue_update(self, row_number: int, column: str, value: str) -> None:
        self.redis.rpush(SHEETS_BATCH_KEY, f"{row_number}|{column}|{value}")

    def process_batch(self) -> None:
        start_time = time.time()
        cell_list = []

        try:
            while True:
                item = self.redis.lpop(SHEETS_BATCH_KEY)
                if not item:
                    break
                row, col, val = item.split("|", 2)
                cell = self.sheets.leads_ws.cell(int(row), self.sheets.header_map[col])
                cell.value = val
                cell_list.append(cell)
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            redis_errors.inc()
            raise

        batch_size.observe(len(cell_list))

        # Process in chunks with exponential backoff
        for i in range(0, len(cell_list), self.chunk_size):
            chunk = cell_list[i : i + self.chunk_size]
            chunk_start = time.time()

            @with_retry(error_counter=sheets_errors)
            def update_chunk():
                self.sheets.leads_ws.update_cells(chunk)

            update_chunk()
            batch_duration.observe(time.time() - chunk_start)

        batch_duration.observe(time.time() - start_time)
