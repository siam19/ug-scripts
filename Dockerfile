# ---------------------------------------------------------------------------
# Stage 1: Build the frontend web application with Bun
# ---------------------------------------------------------------------------
FROM oven/bun:1-alpine AS frontend-builder
WORKDIR /build

# Copy monorepo dependency manifests
COPY package.json bun.lock* ./
COPY packages/api-types/package.json ./packages/api-types/
COPY apps/web/package.json ./apps/web/

# Install workspace dependencies
RUN bun install --frozen-lockfile || bun install

# Copy source code needed for frontend build
COPY packages/api-types ./packages/api-types
COPY apps/web ./apps/web

# Build frontend bundle (empty VITE_API_URL targets same-origin FastAPI)
ENV VITE_API_URL=""
ENV VITE_API_KEY=""
RUN cd apps/web && bun run build

# ---------------------------------------------------------------------------
# Stage 2: Python FastAPI Runtime
# ---------------------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install Python dependencies first for Docker caching
COPY apps/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY apps/api/ ./

# Copy root environment configuration into container
COPY .env* ./
RUN if [ -f .env ]; then echo "Loaded .env into container"; elif [ -f .env.example ]; then cp .env.example .env; fi

# Copy built frontend static assets into static directory for FastAPI serving
COPY --from=frontend-builder /build/apps/web/dist ./static

EXPOSE 8080

# Cloud Run injects PORT dynamically (defaults to 8080)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
