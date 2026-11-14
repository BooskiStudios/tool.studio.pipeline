# syntax=docker/dockerfile:1
# Production image for Booski Core. Built and smoke-tested by CI (.github/workflows/ci.yml).
# Base images are pinned to exact versions; bump them deliberately.

FROM ghcr.io/astral-sh/uv:0.13.6 AS uv

FROM python:3.13.17-slim-bookworm AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /src
# Dependencies first, so code changes don't invalidate this layer.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.13.17-slim-bookworm AS runtime
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin booski
COPY --from=build --chown=root:root /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
USER booski
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=2).status != 200)"]
# Listens on all interfaces *inside* the container. Publish the port to 127.0.0.1 only until
# authentication exists (docker-compose.yml does this).
CMD ["booski", "serve", "--host", "0.0.0.0", "--port", "8000", "--allow-non-loopback"]
