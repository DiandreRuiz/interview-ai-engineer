# fda-regulations

Python 3.13 package for the Modicus takehome: warning-letter ingest, hybrid retrieval, and a small FastAPI search API. Assignment goals and grading criteria are in the repository root [README.md](../README.md).

**Code review:** for a single walkthrough of layers and data flow, see [`docs/mental-model-code-review.md`](docs/mental-model-code-review.md). The implementation plan lives at [`context/plans/implementation-plan.md`](../context/plans/implementation-plan.md).

---

## Setup

From this directory:

```bash
cp .env.example .env
uv sync
```

**`.env`:** `uv run` loads it automatically (in addition to **`pydantic-settings`** for the app). It includes **`PYTHONPATH=src`** so imports work everywhere; on some **macOS** setups, Python **ignores “hidden” `.pth` files** in `site-packages`, which would otherwise break editable installs (see [cpython#148121](https://github.com/python/cpython/issues/148121)). **CI** does not rely on `.env`: **`pytest`** uses `pythonpath = ["src"]` in `pyproject.toml`.

For local development **without** a built index, set `REQUIRE_ARTIFACTS=false` in `.env`.

---

## Corpus, index, and manifests (terminology)

| Concept | On disk (typical) | Role |
|--------|-------------------|------|
| **Corpus** | `{ARTIFACT_ROOT}/corpus/letters.jsonl` + `corpus_manifest.json` | Raw per-letter **HTML** and listing metadata. Canonical offline store for re-chunking and re-indexing. |
| **Index** | `{ARTIFACT_ROOT}/index_manifest.json`, `chunks.jsonl`, `embeddings.npy`, `chunk_order.json` | **Searchable** paragraph chunks + dense vectors. The API loads this set, not the corpus JSONL. |
| **Corpus manifest** | `corpus_manifest.json` | Small JSON: schema version, `built_at_utc`, `letter_count`, `source` (e.g. `fda-scrape`, `fda-rehydrate`). |
| **Index manifest** | `index_manifest.json` | Small JSON: schema version, `index_backend`, `embedding_model_id`, chunk count, paths to sidecars. Validated at API startup when `REQUIRE_ARTIFACTS=true`. |

Human-readable **text previews** from `--preview-dir` go under `reports/ingest_preview/` (gitignored); they are for QA only, not used for search.

---

## Environment variables (see `.env.example`)

All batch CLIs and the API read **`fda_regulations.config.Settings`** (pydantic-settings), including from `.env` when present. `uv run` also loads `.env` (see Setup).

| Variable | Purpose |
|----------|---------|
| `PYTHONPATH` | Set to `src` in `.env.example`. Ensures the `src/` layout is importable via `uv run` (see Setup). Not read by application code. |
| `ARTIFACT_ROOT` | Root for **index** files and default `{ARTIFACT_ROOT}/corpus` unless overridden. |
| `INGEST_CORPUS_DIR` | Optional override for corpus directory (default: `{ARTIFACT_ROOT}/corpus`). |
| `REQUIRE_ARTIFACTS` | If `true`, FastAPI startup requires a valid hybrid `index_manifest.json` under `ARTIFACT_ROOT`. |
| `INDEX_EMBEDDING_MODEL` | Sentence-transformers model id for `fda-build-index` / rehydrate (unless overridden by CLI). |
| `INGEST_MAX_LISTING_PAGES` | Cap DataTables AJAX batches after the hub shell GET; **unset** = page until the catalog ends. |
| `INGEST_MAX_LETTERS` | Cap letters fetched after discovery; **unset** = no cap. |
| `INGEST_REQUEST_DELAY_SECONDS` | Delay between HTTP calls during ingest (politeness). |
| `INGEST_LISTING_BATCH_SIZE` | DataTables `length` parameter (1–500). |
| `FDA_USER_AGENT` | User-Agent for FDA HTTP requests. |
| `RRF_K`, `SEARCH_TOP_K_SPARSE`, `SEARCH_TOP_K_DENSE` | Query-time fusion and candidate pool sizes for the loaded retriever. |

---

## Where the commands are defined

Console scripts are registered in `pyproject.toml` under `[project.scripts]`:

| Command | Implementation |
|---------|------------------|
| `fda-scrape` | `fda_regulations.cli.scrape:main` |
| `fda-build-index` | `fda_regulations.cli.build_index:main` |
| `fda-rehydrate` | `fda_regulations.cli.rehydrate:main` |

Run **`uv run <command> --help`** anytime for argparse text that matches the code.

**Scripts:** `scripts/rehydrate_warning_letters.py` is a thin wrapper around **`fda-rehydrate`** (for cron paths that invoke a file); prefer **`uv run fda-rehydrate`**.

Batch CLIs use **Rich** throughout: **`RichHandler`** for `logging` on stderr, **Rich progress** during live scrapes, and **panels / tables** on stdout for milestones and summaries.

---

## `fda-scrape` — listing + per-letter HTML

Fetches the FDA warning-letters **hub page** once, then **DataTables AJAX** (`/datatables/views/ajax` on the same host) with `start` / `length` to discover letter URLs, then **one GET per letter** for HTML.

**Flags:**

| Flag | Meaning |
|------|---------|
| `--max-pages N` | Override `INGEST_MAX_LISTING_PAGES` for this run (cap AJAX batches after shell GET). |
| `--max-letters N` | Override `INGEST_MAX_LETTERS` for this run (max letters to fetch after discovery). |
| `--write-corpus` | After scrape, write `letters.jsonl` and `corpus_manifest.json` under the resolved corpus directory (`INGEST_CORPUS_DIR` or `{ARTIFACT_ROOT}/corpus`). |
| `--preview-dir DIR` | Write one `<letter_id>.txt` per letter (main text from `article#main-content`) under `DIR`. |

**Examples:**

```bash
# Small dev run (caps via CLI)
uv run fda-scrape --max-pages 2 --max-letters 5

# Same, plus persist corpus
uv run fda-scrape --max-pages 2 --max-letters 5 --write-corpus

# Plain-text previews for manual QA (directory is gitignored by default)
uv run fda-scrape --max-pages 2 --max-letters 5 --preview-dir reports/ingest_preview
```

**Full-catalog behavior:** leave `INGEST_MAX_LISTING_PAGES` and `INGEST_MAX_LETTERS` **unset** in `.env` and omit `--max-pages` / `--max-letters`. Expect a long, polite run. **`run_ingest`** always shows **Rich** progress on stderr (listing row range vs catalog total + detail GET bar); stdout gets a banner and completion table after the run.

If `uv run` cannot import the package, confirm `.env` exists (copy from `.env.example`) so `PYTHONPATH=src` is set, then run `uv sync` again.

**CI:** tests do **not** call the live FDA network (fixtures + RESPX). See `src/fda_regulations/ingest/README.md` for scrape internals.

---

## `fda-build-index` — corpus → chunks → hybrid index

Reads letters (from **disk** or from a **live scrape**), runs paragraph chunking + CFR regex metadata, encodes embeddings, writes hybrid artifacts under `--artifact-root` (or `ARTIFACT_ROOT`).

**Flags:**

| Flag | Meaning |
|------|---------|
| `--artifact-root DIR` | Output directory for `index_manifest.json`, `chunks.jsonl`, `embeddings.npy`, `chunk_order.json`. Default: `ARTIFACT_ROOT` from settings. |
| `--corpus-dir DIR` | Directory containing `letters.jsonl` (and `corpus_manifest.json`). Used when **not** using `--scrape-first`. Default: resolved `INGEST_CORPUS_DIR`. |
| `--embedding-model ID` | Override `INDEX_EMBEDDING_MODEL` for this build. |
| `--scrape-first` | Call `run_ingest(settings)` first (live FDA). Uses **current** `Settings`, including `INGEST_MAX_*` caps from `.env` unless unset. |
| `--write-corpus` | Only meaningful **with** `--scrape-first`: after scraping, write corpus JSONL to `--corpus-dir` / default corpus dir. |
| `--report PATH` | Write a markdown phase-1 summary (letter count, chunk count, CFR-regex coverage on chunks, paths, model id). |

**Flows:**

```bash
# Index from an existing corpus on disk (no network)
uv run fda-build-index --artifact-root ./artifacts

# Live scrape, then index (respects .env ingest caps)
uv run fda-build-index --artifact-root ./artifacts --scrape-first

# Live scrape, persist corpus, index, and write a report
uv run fda-build-index --artifact-root ./artifacts --scrape-first --write-corpus --report reports/phase1.md
```

The first run may download the **sentence-transformers** model; indexing is CPU-oriented and scales with corpus size.

---

## `fda-rehydrate` — incremental catch-up

**When to use:** you already have a corpus and want **only new** warning letters (by `letter_id` slug) without re-fetching the whole catalog’s HTML.

**Behavior:**

- Loads existing `letters.jsonl` (if present); builds the set of known `letter_id`s.
- Runs **`run_ingest_new_letters`**, which scans the **full** listing but **skips** detail GETs for ids already in the corpus. **`INGEST_MAX_LISTING_PAGES` and `INGEST_MAX_LETTERS` are forced off** for this command so every listing row can be considered.
- If **no** new letters: exits without rewriting corpus or index.
- If there are new letters: merges **existing + new**, rewrites corpus (`source` label `fda-rehydrate`), **rebuilds the full hybrid index** (full re-embed of all chunks).

**Flags:** same shape as `fda-build-index` for `--artifact-root`, `--corpus-dir`, `--embedding-model`, and `--report`.

```bash
cd fda-regulations
uv run fda-rehydrate --artifact-root ./artifacts
```

Prefer running from **`fda-regulations/`** so `.env` resolves correctly.

**vs `fda-build-index --scrape-first`:** the latter re-downloads every letter in scope of caps; rehydrate minimizes detail fetches for **missing** ids only. For an **empty** corpus, rehydrate still fetches all letters (nothing to skip), but the usual first-time path is **`fda-build-index --scrape-first --write-corpus`** for clarity.

---

## Reviewer cheat sheet (common tasks)

| Goal | Command |
|------|---------|
| Install dependencies | `cp .env.example .env` then `uv sync` |
| Lint / types / tests | `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run pytest` |
| Small scrape (no corpus file) | `uv run fda-scrape --max-pages 2 --max-letters 5` |
| Build index from existing corpus | `uv run fda-build-index --artifact-root ./artifacts` |
| Full pipeline: scrape + corpus + index + report | `uv run fda-build-index --artifact-root ./artifacts --scrape-first --write-corpus --report reports/phase1.md` |
| Add only new letters + rebuild index | `uv run fda-rehydrate --artifact-root ./artifacts` |
| Run API (native) | `uv run uvicorn fda_regulations.app.main:app --reload --host 0.0.0.0 --port 8000` (needs `.env` in this directory so `PYTHONPATH=src` is set) |
| Run API (Docker) | `docker compose up --build` from the **repository root** (requires artifacts built first; see Docker section below) |

From the repository root (monorepo):

```bash
cp fda-regulations/.env.example fda-regulations/.env
uv --directory fda-regulations sync
uv --directory fda-regulations run pytest
```

---

## Run the API

From **`fda-regulations/`**, with **`.env`** present (see **Setup** — `uv run` loads it):

```bash
uv run uvicorn fda_regulations.app.main:app --reload --host 0.0.0.0 --port 8000
```

- OpenAPI UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health: `GET /health`
- Search: `POST /search` with JSON body `{"query": "…", "top_k": 10}`

With `REQUIRE_ARTIFACTS=true` (default), startup loads a **hybrid** index from `ARTIFACT_ROOT`. If the manifest or sidecars are missing, startup fails with a clear error.

---

## Docker

The API runs in Docker via a two-stage build (`Dockerfile` at the repository root). Stage 1 installs production dependencies with `uv`; Stage 2 copies only the `.venv` and source into a slim runtime image with a non-root user.

**Prerequisites:** build the index artifacts on the host first (see `fda-build-index` above). The container bind-mounts `fda-regulations/artifacts/` read-only at runtime — artifacts are not baked into the image.

From the **repository root**:

```bash
docker compose up --build
```

- API available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health: `GET /health`
- Search: `POST /search` with `{"query": "…", "top_k": 10}`

The `docker-compose.yml` sets `ARTIFACT_ROOT=/app/artifacts` and `REQUIRE_ARTIFACTS=true`. Startup loads the hybrid index (BM25 + embeddings); the healthcheck accounts for the ~60 s cold-start on large indexes.

To stop: `docker compose down`.

---

## Package map

| Area | Package / module |
|------|------------------|
| Scrape | `fda_regulations.ingest.scrape` (`run_ingest`, `run_ingest_new_letters`, …) |
| Corpus I/O | `fda_regulations.ingest.corpus` |
| Chunking | `fda_regulations.chunking` (`chunk_raw_letter`, `ChunkRecord`, …) |
| Index build / load | `fda_regulations.index` |
| Corpus → all chunk records | **`raw_letters_to_chunks`** (defined in **`fda_regulations.chunking`**, not a separate module) |
| Phase-1 markdown report | `fda_regulations.reporting.write_phase1_ingest_report` |

---

## Next steps (interview — not implemented here)

For **what we would add next** after this PoC, see **`context/plans/implementation-plan.md`** → “Next steps (not in PoC — say this in interviews)”:

1. **CFR strings per chunk** — stored as metadata (`cfr_citations`) and returned in `POST /search` responses; retrieval ranking ignores them today but they enable downstream filtering, boosting, or citation display.
2. **Taxonomy / weak supervision** — the older plan (small label vocab, CFR-prefix rules + keyword overlap, optional search filter/boost) we dropped to keep the stack easy to explain; good to walk through as a deliberate simplification.
