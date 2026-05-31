# Stage 1 — build the React frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# Stage 2 — Python runtime + frontend dist
FROM python:3.11-slim
WORKDIR /app/backend

# System deps (pandas needs gcc, PyPDF2 needs nothing extra)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend source
COPY backend/ ./

# Frontend build output (FastAPI serves it at /  in production)
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Writable data directory for scan_store.json
RUN mkdir -p /app/backend/data

EXPOSE 8000

# PORT env var is set by Render/Railway; fall back to 8000 locally
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
