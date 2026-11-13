FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run entrypoint script that seeds database and starts uvicorn
EXPOSE 8000

CMD ["sh", "-c", "python -m app.seed || true && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
