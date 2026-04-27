# syntax=docker/dockerfile:1

# --- Frontend build stage ---
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Runtime stage ---
FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CRYPTODASH_DB_PATH=/app/data/cryptodash.db \
    CRYPTODASH_HOST=0.0.0.0 \
    CRYPTODASH_PORT=8000

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY run.py alembic.ini ./
COPY --from=frontend /build/dist ./frontend/dist

RUN useradd -u 1000 -m -s /usr/sbin/nologin cryptodash \
    && mkdir -p /app/data \
    && chown -R cryptodash:cryptodash /app

USER cryptodash

VOLUME ["/app/data"]
EXPOSE 8000

CMD ["python", "run.py"]
