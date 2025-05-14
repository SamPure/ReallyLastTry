FROM python:3.11-slim

WORKDIR /app

# Install build deps and curl for healthcheck
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose dynamic port (Railway injects $PORT)
EXPOSE ${PORT:-8000}

# Healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Use shell form to ensure $PORT is expanded
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
