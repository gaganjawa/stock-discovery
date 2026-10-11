FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1

WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt
COPY shared /app/shared
COPY worker/worker /app/worker
ENV PYTHONPATH=/app/shared
USER 10001:10001
CMD ["python", "-m", "worker.main"]
