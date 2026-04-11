---
name: ruff-pyright-ci
description: Configures Ruff linter and formatter plus Pyright type checking in pyproject or dedicated config files for strict narrow types in fda-regulations. Use when setting up CI, fixing pyright errors, choosing ruff rule sets, or aligning with the employer README evaluation of uv and type hints.
---

# Ruff and Pyright (project configuration)

**Canonical documentation**

- [Ruff](https://docs.astral.sh/ruff/) — linter + formatter (shares tooling lineage with uv)
- [Ruff rules](https://docs.astral.sh/ruff/rules/)
- [Ruff configuration](https://docs.astral.sh/ruff/configuration/) (CLI flags mirror **`ruff check`** / **`ruff format`** subcommands)
- [Pyright configuration](https://github.com/microsoft/pyright/blob/main/docs/configuration.md)

The employer README calls out **effective use of type hints** and **`uv`**. Ruff + Pyright are the default quality gates ([python-best-practices](../python-best-practices/SKILL.md)).

## Ruff (`pyproject.toml`)

Typical `[tool.ruff]` sections:

```toml
[tool.ruff]
target-version = "py313"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = []

[tool.ruff.format]
quote-style = "double"
```

- Run **`uv run ruff check .`** and **`uv run ruff format .`** (or `--check` in CI).
- Extend **select** gradually (`ANN`, `TCH`, etc.) if the team wants stricter typing style—avoid blocking the PoC on noisy rules without autofix.

## Pyright

Prefer **`[tool.pyright]`** in **`fda-regulations/pyproject.toml`** when you want a single config file:

```toml
[tool.pyright]
include = ["src"]
exclude = ["**/__pycache__", ".venv"]
pythonVersion = "3.13"
typeCheckingMode = "standard" # fda-regulations uses standard; tighten to "strict" only if the team wants
```

- **`pyrightconfig.json`** in the same directory **overrides** `pyproject` if both exist—pick one source of truth.
- Align **`include`** with your package layout (`src/fda_regulations`).

## CI

Invoke via **`uv run`** in GitHub Actions ([github-actions-uv-python](../github-actions-uv-python/SKILL.md)).

## Cross-references

- Typed boundaries: [pydantic-v2-validation](../pydantic-v2-validation/SKILL.md).
- Tests: [pytest-http-fixtures](../pytest-http-fixtures/SKILL.md).
