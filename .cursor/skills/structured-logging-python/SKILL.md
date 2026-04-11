---
name: structured-logging-python
description: Adds structured application logging for search queries, latency, and top chunk IDs using stdlib logging or optional structlog, preferring logs before Langfuse in the Modicus PoC. Use when instrumenting FastAPI search, ingest pipelines, or debugging hybrid retrieval without paid observability.
---

# Structured logging (PoC observability)

**References**

- [logging — Logging facility](https://docs.python.org/3/library/logging.html)
- [Logging cookbook](https://docs.python.org/3/howto/logging-cookbook.html) (formatters, handlers, context)
- [structlog](https://www.structlog.org/) (optional third-party structured logs)
- Project preference: [implementation-plan.md](../../../context/plans/implementation-plan.md) (structured logs before optional Langfuse)

The implementation plan prefers **structured application logs** first. **Langfuse** remains optional; if adopted, use the Cursor **Langfuse** skill in addition—do not block the PoC on external observability SaaS.

## What to log (search path)

At **INFO**, log one line (or JSON object) per query with fields such as:

- **`query`** (truncated if very long)
- **`latency_ms`**
- **`top_chunk_ids`** (ordered, capped length)
- **`result_count`**
- Optional **filter context** if the API gains metadata filters later

Avoid logging **secrets** or full personal data from letters beyond what the report needs.

## Stdlib pattern

Use **`logging.getLogger(__name__)`**, JSON formatter in production containers if desired, or key=value pairs for grep-friendly PoCs:

```python
import logging
import time

log = logging.getLogger(__name__)

def search(...) -> list[Hit]:
    start = time.perf_counter()
    try:
        hits = ...
        log.info(
            "search_complete latency_ms=%.1f top=%s",
            (time.perf_counter() - start) * 1000,
            [h.chunk_id for h in hits[:10]],
        )
        return hits
    except Exception:
        log.exception("search_failed")
        raise
```

## FastAPI correlation

- Add middleware or dependencies to attach **`request_id`** (UUID) and include it in log lines for tracing a single call ([fastapi-async-api](../fastapi-async-api/SKILL.md)).

## Optional structlog

- If you adopt **structlog**, bind **`request_id`** once per request and emit JSON to stdout for Docker log drivers.

## Cross-references

- Container logs: [docker-desktop-python](../docker-desktop-python/SKILL.md).
