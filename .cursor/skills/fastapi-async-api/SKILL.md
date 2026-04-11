---
name: fastapi-async-api
description: Builds async FastAPI services with dependency injection, lifespan hooks for indexes, POST search endpoints, OpenAPI, and Uvicorn deployment. Use when exposing hybrid search over HTTP, loading BM25 or embedding indexes at startup, or documenting APIs for the fda-regulations PoC.
---

# FastAPI — async API for search and health

**Canonical documentation**

- [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/)
- [FastAPI reference](https://fastapi.tiangolo.com/reference/)
- [Lifespan events](https://fastapi.tiangolo.com/advanced/events/) (recommended; `@app.on_event("startup")` / `"shutdown"` are legacy)
- [Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) (`Depends`, shared clients)
- [Handling errors](https://fastapi.tiangolo.com/tutorial/handling-errors/) (`HTTPException`)
- [Starlette lifespan](https://www.starlette.dev/lifespan/) (underlying ASGI behavior)

**fda-regulations pins** (see `pyproject.toml`): **FastAPI ≥0.115**, **Uvicorn ≥0.32**, **Python 3.13**.

This project’s **`POST /search`** returns ranked chunks with **citations** (`letter_url`, `chunk_id`, `paragraph_index`, `snippet`). Keep handlers **thin**: validate input, call the retriever (often via **`asyncio.to_thread`** for sync BM25/embeddings work), map to response models.

## App structure

- Prefer an **`app` factory** (`create_app()`) when tests need overrides, or a module-level `app = FastAPI(...)` for minimal PoCs.
- Register **routers** under `app.include_router(...)` for `search` vs `health`.

## Lifespan (load indexes once)

Use **`@asynccontextmanager` lifespan** to load BM25 corpus, embedding model, or mmap’d vectors **once** at startup and attach to `app.state`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.retriever = build_retriever(...)
    yield
    # optional: close clients

app = FastAPI(lifespan=lifespan)
```

Avoid heavy work per request.

## Request and response models

- Define **`BaseModel`** bodies and responses in Pydantic v2 ([pydantic-v2-validation](../pydantic-v2-validation/SKILL.md)); use **`response_model=`** on routes for stable OpenAPI and serialization.
- Use **`Literal`** for enums exposed in JSON (e.g. classification method).

## Async vs sync

- **Async route handlers** for I/O-bound work (`await` HTTPX, async file I/O if used).
- If a library is **CPU-bound and sync** (some embedding calls), run in **`asyncio.to_thread()`** ([stdlib](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)) or a small process pool to avoid blocking the event loop—document the choice.

## Errors

- Raise **`HTTPException`** with appropriate status codes for bad queries or empty index.
- Do not leak stack traces in responses in production containers; log server-side ([structured-logging-python](../structured-logging-python/SKILL.md)).

## Running locally and in Docker

```bash
cd fda-regulations && uv run uvicorn fda_regulations.app.main:app --reload --host 0.0.0.0 --port 8000
```

Adjust import path to your package. In Docker, use **`--host 0.0.0.0`** and match the exposed port ([docker-desktop-python](../docker-desktop-python/SKILL.md)). See [Uvicorn settings](https://www.uvicorn.org/settings/).

## Cross-references

- Types and settings: [pydantic-v2-validation](../pydantic-v2-validation/SKILL.md).
- Retrieval logic stays in Python modules, not in route bodies: [hybrid-search-rrf-bm25](../hybrid-search-rrf-bm25/SKILL.md), [sentence-transformers-local](../sentence-transformers-local/SKILL.md).
