# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Build React frontend
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --prefer-offline
COPY frontend/ .
RUN npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Python API + serve static files
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.10-slim AS api

# System deps for building bcrypt / cryptography wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
# Pin bcrypt before installing requirements so passlib resolves correctly
RUN pip install --no-cache-dir bcrypt==4.0.1 && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Copy compiled frontend assets into FastAPI static directory
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Ensure logs directory exists
RUN mkdir -p logs

# Non-root user for security
RUN useradd -m -u 1001 pharmaiq && chown -R pharmaiq:pharmaiq /app
USER pharmaiq

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
