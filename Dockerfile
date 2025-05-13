FROM python:3.11-slim

WORKDIR /app

# Install build deps only if you need C extensions
RUN apt-get update && apt-get install -y gcc make && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose dynamic port (Railway injects $PORT)
EXPOSE ${PORT:-8000}

# Healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Use shell form to ensure $PORT is expanded
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
