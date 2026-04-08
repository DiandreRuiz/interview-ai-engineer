---
name: docker-desktop-python
description: Builds and runs Python 3.13 services on macOS with Docker Desktop—Dockerfile patterns, non-root user, healthchecks, uvicorn, and .dockerignore. Use when adding a Dockerfile, docker-compose, containerizing fda-regulations, or when the assignment requires the service to run locally with Docker Desktop.
---

# Docker Desktop and Python containers (this project)

**Official references**

- [Dockerfile best practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker language guide: Python](https://docs.docker.com/language/python/)
- [Uvicorn settings](https://www.uvicorn.org/settings/) (ASGI server for FastAPI)

This repo’s assignment expects the solution to **build and run on macOS with Docker Desktop**. Prefer a **small, reproducible** image over a full dev image.

## Base image and Python version

- Use **`python:3.13-slim`** (or **`python:3.13-slim-bookworm`**) unless you need extra system libraries for lxml/torch; then install only the required `apt` packages in the same `RUN` layer and clean lists to keep layers small.
- Pin **major.minor** in the `FROM` line so rebuilds are predictable.

## Process and environment

- Set **`ENV PYTHONUNBUFFERED=1`** so logs appear promptly in `docker logs`.
- Set **`ENV PYTHONDONTWRITEBYTECODE=1`** to avoid writing `.pyc` into the image when appropriate.
- Prefer **`CMD` in exec form**: e.g. `CMD ["uvicorn", "fda_regulations.app.main:app", "--host", "0.0.0.0", "--port", "8000"]` (adjust module path to your package).

## Non-root user

- Create a dedicated user (e.g. `appuser`), `chown` the app directory, and **`USER`** before `CMD`. Avoid running as root in the container.

## Dependencies with uv (recommended for this repo)

The `fda-regulations` project uses **uv**. Typical patterns:

- **Multi-stage:** stage 1 installs uv + deps (`uv sync --frozen` or `uv sync --locked` per [uv docs](https://docs.astral.sh/uv/)); stage 2 copies `.venv` or wheel installs into a slim runtime. Alternatively copy the project and run `uv sync` in one stage if simplicity beats image size for a PoC.
- From the **repository root**, document commands that set the project directory, e.g. `uv --directory fda-regulations sync`, matching [uv-packaging](../uv-packaging/SKILL.md).

Verify the exact **`uv sync`** flags in the [uv CLI reference](https://docs.astral.sh/uv/reference/cli/); Astral’s GitHub Actions guide uses **`uv sync --locked`** for reproducible installs.

## .dockerignore

Exclude at least: `.venv`, `__pycache__`, `.git`, `.pytest_cache`, `.ruff_cache`, `*.pyc`, local `data/` or large artifacts if not needed in the image. Keeps build context small and avoids leaking secrets.

## Healthcheck (API PoC)

For a FastAPI service, a simple HTTP check helps Docker Desktop and orchestrators:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1
```

Adjust path/port to match your app; prefer a **`/health`** route that does not depend on external FDA calls.

## Local development vs CI

- **Dev:** bind-mount source for hot reload only if documented; many PoCs use **`docker compose`** with a volume over `fda-regulations/src`.
- **CI / reproducible runs:** **`COPY`** the tree and install from the lockfile so the image matches committed deps.

## Cross-references

- Run and type checks: [python-best-practices](../python-best-practices/SKILL.md), [uv-packaging](../uv-packaging/SKILL.md).
- API process model: [fastapi-async-api](../fastapi-async-api/SKILL.md).
