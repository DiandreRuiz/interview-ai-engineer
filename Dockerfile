# ---------- Stage 1: builder ----------
FROM python:3.13-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Layer-cache: deps re-install only when lock changes.
COPY fda-regulations/pyproject.toml fda-regulations/uv.lock fda-regulations/README.md ./
RUN uv sync --locked --no-dev --no-install-project

# ---------- Stage 2: runtime ----------
FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN useradd --create-home appuser

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY fda-regulations/src/ /app/src/

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH=/app/src

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "fda_regulations.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
