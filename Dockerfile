FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ARG CACHEBUST=2026-04-07-1030
COPY . .
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
