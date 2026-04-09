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

## Scrape warning letters (batch CLI)

Fetches the FDA **listing** table (`?page=0`, `?page=1`, …) and **one GET per letter** for HTML. Use caps while developing; omit caps for a **full-catalog** run (slow, be polite with `INGEST_REQUEST_DELAY_SECONDS`).

```bash
uv run fda-scrape --max-pages 2 --max-letters 5
```

Write **plain-text previews** (body extracted from `article#main-content`) for each letter:

```bash
uv run fda-scrape --max-pages 2 --max-letters 5 --preview-dir ../reports/ingest_preview
```

If `uv run fda-scrape` fails to import the package, use `PYTHONPATH=src uv run python -m fda_regulations.cli.scrape …` or run `uv pip install -e .` once from `fda-regulations/`.

See **`context/plans/implementation-plan.md`** (Warning letter ingestion), **`src/fda_regulations/ingest/README.md`** (scrape layout), and **`.env.example`** for env vars. Import the batch scraper from **`fda_regulations.ingest.scrape`**. Default **CI tests do not call FDA** (fixtures + RESPX).
