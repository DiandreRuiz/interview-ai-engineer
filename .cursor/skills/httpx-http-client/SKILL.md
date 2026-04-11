---
name: httpx-http-client
description: Uses HTTPX for sync and async HTTP to FDA sites and APIs—AsyncClient lifecycle, timeouts, connection limits, retries, and streaming. Use when implementing ingest in fda-regulations, wiring HTTP inside FastAPI, or replacing requests with a typed modern client.
---

# HTTPX — HTTP client for ingest and services

**Canonical documentation**

- [HTTPX](https://www.python-httpx.org/)
- [Quickstart](https://www.python-httpx.org/quickstart/)
- [Async support](https://www.python-httpx.org/async/)
- [API / developer interface](https://www.python-httpx.org/api/)
- [Compatibility with Requests](https://www.python-httpx.org/compatibility/) (helpful when porting call sites)

**fda-regulations pins** (see `pyproject.toml`): **HTTPX ≥0.28** (check [release notes](https://github.com/encode/httpx/blob/master/CHANGELOG.md) when upgrading across minors).

HTTPX supports **sync and async** APIs, HTTP/1.1 and HTTP/2, and is **fully type-annotated**. Prefer it over `requests` for new code in this repo when async fits the call site.

## Client lifecycle

- **Async:** use one shared **`AsyncClient`** per scope (app lifespan or task), not per request in a hot loop:

```python
async with httpx.AsyncClient() as client:
    response = await client.get(url)
    response.raise_for_status()
```

- **Sync:** `with httpx.Client() as client:` for scripts and CLI ingest.

Reuse clients to benefit from **connection pooling**.

## Timeouts

Always set **timeouts** for external FDA calls (network stalls should not hang the API):

```python
timeout = httpx.Timeout(10.0, connect=5.0)
client = httpx.AsyncClient(timeout=timeout)
```

See [Timeouts](https://www.python-httpx.org/advanced/timeouts/) for fine-grained connect/read/pool settings.

## Limits and headers

- Tune **`limits=httpx.Limits(max_connections=..., max_keepalive_connections=...)`** if you run concurrent fetches.
- Set a realistic **`User-Agent`** identifying the PoC; avoid impersonating browsers.

## Retries

HTTPX does not retry by default. For transient failures, use a small **tenacity** loop or wrap calls at the ingest layer—keep behavior **deterministic in tests** (mock or fixture responses).

## Streaming

For large responses, use **`client.stream("GET", url)`** and iterate with async iteration (`aiter_bytes` / `aiter_text`) per [Async streaming](https://www.python-httpx.org/async/#streaming-responses).

## Testing

- Do not call live FDA URLs in default CI. Use **RESPX** or **pytest-httpx** ([pytest-http-fixtures](../pytest-http-fixtures/SKILL.md)).

## Cross-references

- Parse HTML after fetch: [html-parsing-ingest](../html-parsing-ingest/SKILL.md).
- FastAPI integration: [fastapi-async-api](../fastapi-async-api/SKILL.md).
