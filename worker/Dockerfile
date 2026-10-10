FROM python:3.12-slim

WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY shared /app/shared
COPY worker/worker /app/worker
ENV PYTHONPATH=/app/shared
CMD ["python", "-m", "worker.main"]
