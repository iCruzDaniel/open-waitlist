# =============================================================================
# Stage 0 — Frontend builder (Node): compile admin panel
# =============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /build

# Copy package files first for layer caching
COPY admin-panel/package*.json ./
RUN if [ -f package.json ]; then npm ci; else mkdir -p /tmp/dummy; fi

# Copy full source and build
COPY admin-panel/ ./
RUN if [ -f package.json ]; then \
        npm run build && \
        rm -rf node_modules; \
    else \
        mkdir -p dist; \
    fi


# =============================================================================
# Stage 1 — Python builder: install dependencies
# =============================================================================
FROM python:3.12-slim AS builder

ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN --mount=from=ghcr.io/astral-sh/uv:0.6,source=/uv,target=/bin/uv \
    apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install project dependencies
COPY pyproject.toml uv.lock ./
RUN --mount=from=ghcr.io/astral-sh/uv:0.6,source=/uv,target=/bin/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Final sync so app is registered in .venv
RUN --mount=from=ghcr.io/astral-sh/uv:0.6,source=/uv,target=/bin/uv \
    uv sync --frozen --no-dev

# Copy pre-built admin panel from frontend stage
COPY --from=frontend-builder /build/dist/ ./admin-panel/dist/


# =============================================================================
# Stage 2 — Runtime: minimal image
# =============================================================================
FROM python:3.12-slim

# Create non-root user
RUN groupadd -r openwaitlist && useradd -r -g openwaitlist -d /app -s /sbin/nologin openwaitlist

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /build/.venv/ ./.venv/

# Copy application source
COPY --from=builder /build/app/ ./app/

# Copy admin panel static assets if built (stage 0 always produces dist/,
# even if empty — so this COPY never fails)
COPY --from=builder /build/admin-panel/dist/ ./admin-panel/dist/

# Copy Alembic for migrations
COPY --from=builder /build/alembic/ ./alembic/
COPY --from=builder /build/alembic.ini ./

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

USER openwaitlist

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
