FROM python:3.11-slim

WORKDIR /app

# Install build deps only if you need C extensions
RUN apt-get update && apt-get install -y gcc make && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose dynamic port (Railway injects $PORT)
EXPOSE 8000

CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
