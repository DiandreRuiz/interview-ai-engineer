---
name: pytest-http-fixtures
description: Tests fda-regulations with pytest using fixtures, RESPX or pytest-httpx for HTTP mocking, parametrization, and no live FDA network in CI. Use when adding ingest tests, FastAPI route tests, or satisfying the README requirement for ruff, pyright, and pytest in CI.
---

# pytest, HTTP mocking, and fixtures

**Canonical documentation**

- [pytest](https://docs.pytest.org/)
- [RESPX](https://lundberg.github.io/respx/) — mocks **`httpx`** (sync and async) with a pytest-friendly API
- [pytest-httpx](https://colin-b.github.io/pytest_httpx/) — alternative **`httpx`** mock fixture

**Default recommendation for this repo:** **`RESPX`** when tests already use **HTTPX** ([httpx-http-client](../httpx-http-client/SKILL.md)), because it mirrors HTTPX patterns closely. **`pytest-httpx`** is equally valid; pick one per project and stay consistent.

## Principles

- **No live FDA calls** in default CI runs; use **golden HTML/JSON fixtures** under `tests/fixtures/`.
- **Arrange–act–assert**; one logical behavior per test ([python-best-practices](../python-best-practices/SKILL.md)).
- Use **`@pytest.mark.parametrize`** for CFR / chunking / listing edge cases instead of copy-paste.

## HTTP mocking example (RESPX)

```python
import httpx
import pytest
import respx

@pytest.mark.asyncio
async def test_fetch_letter(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("https://www.fda.gov/example-letter").mock(
        return_value=httpx.Response(200, text="<html>...</html>")
    )
    async with httpx.AsyncClient() as client:
        r = await client.get("https://www.fda.gov/example-letter")
    assert r.status_code == 200
```

Register the ASGI app with **`httpx.ASGITransport`** or **`TestClient`** from Starlette/FastAPI for in-process API tests ([FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)).

## Fixtures layout

- **`tests/fixtures/warning_letters/*.html`** — trimmed real or synthetic pages for parser tests.
- **`tests/fixtures/api/*.json`** — Dashboard API samples if used.
- Keep files **small** and **license-safe** (synthetic preferred when possible).

## Optional VCR

- **`pytest-recording` / VCR** patterns can record once and replay; still commit **scrubbed** cassettes without secrets.

## Lint and typecheck in CI

Run **`ruff check`**, **`ruff format --check`**, **`pyright`**, and **`pytest`** via **`uv run`** in GitHub Actions ([github-actions-uv-python](../github-actions-uv-python/SKILL.md), [ruff-pyright-ci](../ruff-pyright-ci/SKILL.md)).

## Cross-references

- FastAPI routes: [fastapi-async-api](../fastapi-async-api/SKILL.md).
- Client under test: [httpx-http-client](../httpx-http-client/SKILL.md).
