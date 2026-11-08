# Lightweight container image for inference service (< 2 GB, CPU-only)
FROM python:3.11-slim

WORKDIR /app

# Ensure non-buffered stdout logging
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install core pinned dependencies
COPY service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir torch==2.3.0+cpu transformers==4.40.0 --index-url https://download.pytorch.org/whl/cpu

# Copy application code and schema (NO weights included)
COPY service/app.py /app/app.py
COPY data/schema.json /app/data/schema.json

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
