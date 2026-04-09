# fda-regulations

Python 3.13 package for the Modicus takehome: warning-letter ingest, hybrid retrieval, and a small FastAPI search API. Assignment goals and grading criteria are in the repository root [README.md](../README.md).

## Setup

From this directory:

```bash
uv sync --group dev
```

Copy `.env.example` to `.env` if you want non-default settings. For local development **without** a built index, set `REQUIRE_ARTIFACTS=false` in `.env`.

## Run the API

```bash
uv run uvicorn fda_regulations.app.main:app --reload --host 0.0.0.0 --port 8000
```

- OpenAPI UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health: `GET /health`
- Search: `POST /search`

With `REQUIRE_ARTIFACTS=true` (default), startup loads a **hybrid** index from `ARTIFACT_ROOT`: `index_manifest.json` must include `index_backend: hybrid_bm25_dense`, `embedding_model_id`, and sidecars (`chunks.jsonl`, `embeddings.npy`, `chunk_order.json`). Build these with **`fda-build-index`** (see below). If the manifest is missing or incomplete, startup fails with a clear error.

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

Fetches the FDA warning-letters **hub page** once, then **DataTables AJAX** (`/datatables/views/ajax` on the same host) with `start` / `length` to discover letter URLs, and **one GET per letter** for HTML. Use caps while developing; omit caps for a **full-catalog** run (slow, be polite with `INGEST_REQUEST_DELAY_SECONDS`).

```bash
uv run fda-scrape --max-pages 2 --max-letters 5
```

Write **plain-text previews** (body extracted from `article#main-content`) for each letter:

```bash
uv run fda-scrape --max-pages 2 --max-letters 5 --preview-dir ../reports/ingest_preview
```

If `uv run fda-scrape` fails to import the package, use `PYTHONPATH=src uv run python -m fda_regulations.cli.scrape …` or run `uv pip install -e .` once from `fda-regulations/`.

See **`context/plans/implementation-plan.md`**, **[`docs/mental-model-code-review.md`](docs/mental-model-code-review.md)** (code-review walkthrough), **`src/fda_regulations/ingest/README.md`**, and **`.env.example`**. **CI tests do not call FDA** (fixtures + RESPX).

## Persist corpus (JSONL)

After a scrape, write raw HTML + metadata under `ARTIFACT_ROOT/corpus` (or `INGEST_CORPUS_DIR`):

```bash
uv run fda-scrape --max-pages 2 --max-letters 5 --write-corpus
```

This creates `letters.jsonl` and `corpus_manifest.json` for offline rebuilds.

## Build hybrid index (batch)

From a corpus directory (default: resolved `INGEST_CORPUS_DIR` / `ARTIFACT_ROOT/corpus`):

```bash
uv run fda-build-index --artifact-root ./artifacts
```

Optional: **`--report path/to/report.md`** emits a short phase-1 stats file (letter count, chunk count, CFR-regex coverage on chunks). To scrape live FDA immediately before indexing (uses env caps and delays):

```bash
uv run fda-build-index --artifact-root ./artifacts --scrape-first --write-corpus
```

The first run downloads the **sentence-transformers** model named in `INDEX_EMBEDDING_MODEL` (default in `.env.example`); indexing is CPU-friendly and may take a while on a large corpus.

Package map: **`fda_regulations.ingest.scrape`** (fetch), **`fda_regulations.ingest.corpus`** (JSONL I/O), **`fda_regulations.chunking`** (paragraphs + CFR regex metadata on each chunk), **`fda_regulations.index`** (hybrid build/load). For a layered diagram and interview cheat sheet, see **[`docs/mental-model-code-review.md`](docs/mental-model-code-review.md)**.

## Next steps (interview — not implemented here)

For **what we would add next** after this PoC, see **`context/plans/implementation-plan.md` → “Next steps (not in PoC — say this in interviews)”**:

1. **CFR strings per chunk** — already stored as metadata (`cfr_citations`); retrieval ignores them today; you can describe using them for richer citations, boosts, or filters later.
2. **Taxonomy / weak supervision** — the older plan (small label vocab, CFR-prefix rules + keyword overlap, optional search filter/boost) we dropped to keep the stack easy to explain; good to walk through as a deliberate simplification.
