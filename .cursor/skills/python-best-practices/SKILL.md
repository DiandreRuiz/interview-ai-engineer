---
name: python-best-practices
description: Applies maintainable Python patterns for typed application code, packaging with uv, tests, and linting. Use when writing or reviewing Python in this repo, especially under fda-regulations/, or when the user asks for Python style, type hints, project layout, or PEP-aligned habits.
---

# Python best practices (this project)

## Defaults for this codebase

- **Python 3.13**; manage env and deps with **`uv`** (`pyproject.toml`, committed lockfile).
- **Narrow types** at boundaries: Pydantic models or `TypedDict` / `Literal` for JSON and enums; avoid untyped `dict` and `Any` where a shape is known.
- **Lint/format/typecheck:** `ruff` + **`pyright`** (or equivalent) in CI; fix what they report for new code.
- **Tests:** `pytest`, fixtures for I/O and external services; no live network in default CI runs.

## Structure and APIs

- **One obvious module responsibility** per file; prefer small pure functions for transforms (parse, classify, fuse scores) and thin I/O at the edges.
- **Public functions and classes:** type hints on all parameters and return values; short docstrings when behavior or invariants are not obvious from names.
- **Imports:** stdlib, third party, local; avoid `from module import *`.
- **Exceptions:** raise specific types; avoid bare `except:`; do not swallow errors without logging or re-raise.

## Types

- Prefer **`list[str]`**, **`dict[str, T]`**, **`X | None`** over `Optional`/`List` from `typing` when valid on 3.13.
- Use **`Literal`** and **`Enum`** (or `StrEnum`) for fixed sets (e.g. classification method, link tier).
- For **JSON from HTTP/files**, validate into models at the boundary; work with instances inward, not raw dicts.

## Data and configuration

- **Secrets:** environment variables + `.env.example`; never commit keys.
- **Configurable thresholds** (e.g. taxonomy score): named constants or settings object, documented in `context/plans/implementation-plan.md` when they affect behavior.

## Tests

- **Arrange–act–assert**; one logical behavior per test; descriptive names (`test_classify_returns_unclassified_when_below_threshold`).
- **Parametrize** similar cases instead of copy-paste.
- **Deterministic** time and randomness (freeze or inject clocks / seeds) when assertions depend on them.

## Performance and clarity

- Prefer **comprehensions and stdlib** when readable; avoid premature micro-optimization.
- **Document** non-obvious algorithm choices (e.g. RRF `k`) in code or the implementation plan.
- **Logging** at INFO for high-level steps, DEBUG for noisy detail; structured fields where useful.

## Anti-patterns to flag

- Mutable default arguments (`def f(x=[]):`).
- Broad `except Exception` without context or re-raise.
- Silent failure on parse/validation.
- God modules mixing HTTP, business logic, and persistence with no seams.

## When in doubt

Match surrounding code style; if the assignment README is silent, choose the boring standard and record the decision in **`context/plans/implementation-plan.md`**.

## Related project skills (`.cursor/skills/`)

For stack-specific guidance (Docker, FDA ingest, FastAPI, hybrid retrieval, CI), see sibling skills such as **`docker-desktop-python`**, **`fda-regulatory-data-sources`**, **`httpx-http-client`**, **`html-parsing-ingest`**, **`fastapi-async-api`**, **`pydantic-v2-validation`**, **`hybrid-search-rrf-bm25`**, **`sentence-transformers-local`**, **`weak-supervision-taxonomy`**, **`pytest-http-fixtures`**, **`github-actions-uv-python`**, **`ruff-pyright-ci`**, and **`structured-logging-python`**.
