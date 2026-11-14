# syntax=docker/dockerfile:1
# Production image for Booski Studios: the Booski Core API plus the built web app, served from one origin.
# Build from the repository root (docker-compose.yml does):  docker build -f backend/Dockerfile .
# Built and smoke-tested by CI (.github/workflows/ci.yml). Base images are pinned; bump them deliberately.

FROM ghcr.io/astral-sh/uv:0.13.6 AS uv

# ---- web app: npm ci + vite build -> /web/dist
FROM node:24.12.0-bookworm-slim AS web
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY index.html tsconfig.json tsconfig.app.json vite.config.ts ./
COPY src ./src
RUN npx tsc -p tsconfig.app.json && npx vite build

# ---- API: dependencies, then the project
FROM python:3.13.17-slim-bookworm AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /src
# Dependencies first, so code changes don't invalidate this layer.
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.13.17-slim-bookworm AS runtime
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin booski
COPY --from=build --chown=root:root /app/.venv /app/.venv
COPY --from=web --chown=root:root /web/dist /app/web
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BOOSKI_FRONTEND_DIST=/app/web
WORKDIR /app
USER booski
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=2).status != 200)"]
# Listens on all interfaces *inside* the container. Publish the port to 127.0.0.1 only, and put an HTTPS
# reverse proxy in front before any other machine connects (see backend/DEPLOYMENT.md).
CMD ["booski", "serve", "--host", "0.0.0.0", "--port", "8000", "--allow-non-loopback"]
