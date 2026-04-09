# fda-regulations

Python 3.13 package for the Modicus takehome: warning-letter ingest, hybrid retrieval, and a small FastAPI search API. Assignment goals and grading criteria are in the repository root [README.md](../README.md).

## Setup

From this directory:

```bash
uv sync --group dev
```

Copy `.env.example` to `.env` if you want non-default settings. For local development without building an index yet, set `REQUIRE_ARTIFACTS=false` in `.env`.

## Run the API

```bash
uv run uvicorn fda_regulations.app.main:app --reload --host 0.0.0.0 --port 8000
```

- OpenAPI UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health: `GET /health`
- Search: `POST /search`

With `REQUIRE_ARTIFACTS=true` (default), the process exits at startup unless `ARTIFACT_ROOT` exists and contains `index_manifest.json` with `"schema_version": 1`. The current retriever is still a **stub** (empty hits) until BM25 + dense + RRF are wired in.

## Quality checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

From the repository root:

```bash
uv --directory fda-regulations sync --group dev
uv --directory fda-regulations run pytest
```
