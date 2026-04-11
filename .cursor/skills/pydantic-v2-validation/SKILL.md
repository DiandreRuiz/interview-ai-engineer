---
name: pydantic-v2-validation
description: Defines Pydantic v2 models and settings for API boundaries, chunk records, search DTOs, Literal enums, and environment configuration. Use when validating JSON from FastAPI or replacing untyped dicts with narrow models in fda-regulations.
---

# Pydantic v2 — models at boundaries

**Canonical documentation**

- [Models](https://docs.pydantic.dev/latest/concepts/models/)
- [Model configuration](https://docs.pydantic.dev/latest/concepts/config/) (`model_config`, `ConfigDict`)
- [`ConfigDict` API reference](https://docs.pydantic.dev/latest/api/config/)
- [Types and validation](https://docs.pydantic.dev/latest/concepts/types/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) (`pydantic-settings` package)

**fda-regulations pins** (see `pyproject.toml`): **pydantic ≥2.10**, **pydantic-settings ≥2.6**.

The employer README expects **narrow types** and avoiding raw **`dict` / `Any`** where a shape is known. Use **Pydantic v2** (`BaseModel`) for HTTP request/response bodies and persisted chunk records loaded into memory.

## Model basics

```python
from pydantic import BaseModel, ConfigDict, Field

class SearchHit(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str
    score: float
    snippet: str
    letter_id: str
    letter_url: str
    paragraph_index: int | None = None
```

- Use **`model_config = ConfigDict(...)`** (not v1 `class Config`).
- Prefer **`extra="forbid"`** on external-facing models when you want strict contracts.

## Literals and enums

- Use **`Literal["ok", "degraded"]`** (or similar) for small closed sets in JSON.
- Use **`StrEnum`** when the set is shared across modules and you want enum behavior in Python.

## JSON and FastAPI

- FastAPI uses Pydantic models for **`Body`**, **`response_model`**, and path/query params. Validate once at the edge; work with model instances inward ([fastapi-async-api](../fastapi-async-api/SKILL.md)).

## When to use `TypedDict` instead

For **internal** structures that mirror JSON but do not need validation on every construction, **`TypedDict`** can be lighter. Prefer Pydantic for **untrusted** input. See [python-best-practices](../python-best-practices/SKILL.md).

## Pydantic Settings (environment)

Install **`pydantic-settings`** and load configuration from environment for Docker and local dev:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    artifact_root: str = "artifacts"
    rrf_k: int = 60
```

- Document every variable in **`.env.example`** (no secrets in git).
- Keep RRF **`k`**, sparse/dense top‑`k`, and embedding model id either in settings or named module constants referenced from [implementation-plan.md](../../../context/plans/implementation-plan.md).

## Cross-references

- Project Python defaults: [python-best-practices](../python-best-practices/SKILL.md).
- Testing validation errors: [pytest-http-fixtures](../pytest-http-fixtures/SKILL.md).
