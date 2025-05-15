import sqlite3
from datetime import datetime
import json
from typing import Dict, List, Optional
import os

class MetricsStore:
    def __init__(self, db_path: str = "metrics.db"):
        """Initialize the metrics store with SQLite database."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    timestamp TEXT PRIMARY KEY,
                    email_queue INTEGER,
                    retry_queue INTEGER,
                    followup_queue INTEGER,
                    emails_sent INTEGER,
                    emails_failed INTEGER,
                    service_health_email INTEGER,
                    service_health_followup INTEGER
                )
            """)

    def store_metrics(self, metrics: Dict[str, float]):
        """Store a new set of metrics."""
        timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO metrics (
                    timestamp, email_queue, retry_queue, followup_queue,
                    emails_sent, emails_failed, service_health_email,
                    service_health_followup
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                int(metrics.get('email_queue_size', 0)),
                int(metrics.get('email_retry_queue_size', 0)),
                int(metrics.get('followup_queue_size', 0)),
                int(metrics.get('emails_sent_total{template="default"}', 0)),
                int(metrics.get('emails_failed_total{error_type="default"}', 0)),
                int(metrics.get('service_health{service="email"}', 0)),
                int(metrics.get('service_health{service="followup"}', 0))
            ))

    def get_recent_metrics(self, limit: int = 100) -> List[Dict]:
        """Retrieve recent metrics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM metrics
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def cleanup_old_metrics(self, days: int = 7):
        """Remove metrics older than specified days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM metrics
                WHERE timestamp < ?
            """, (cutoff,))

    def export_metrics(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
        """Export metrics to JSON format."""
        query = "SELECT * FROM metrics"
        params = []

        if start_date or end_date:
            conditions = []
            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("timestamp <= ?")
                params.append(end_date)
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp ASC"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            columns = [description[0] for description in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return json.dumps(data, indent=2)

    def get_metrics_summary(self) -> Dict:
        """Get summary statistics for metrics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_records,
                    MIN(timestamp) as first_record,
                    MAX(timestamp) as last_record,
                    AVG(email_queue) as avg_email_queue,
                    AVG(retry_queue) as avg_retry_queue,
                    AVG(followup_queue) as avg_followup_queue,
                    SUM(emails_sent) as total_emails_sent,
                    SUM(emails_failed) as total_emails_failed
                FROM metrics
            """)
            return dict(zip([col[0] for col in cursor.description], cursor.fetchone()))
