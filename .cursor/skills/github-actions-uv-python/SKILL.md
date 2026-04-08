---
name: github-actions-uv-python
description: Configures GitHub Actions for Python projects using astral-sh setup-uv, uv sync locked installs, uv run for pytest ruff and pyright, and optional cache. Use when adding CI to the Modicus repo, reproducing the README toolchain on ubuntu-latest, or pinning uv versions in workflows.
---

# GitHub Actions with uv (Python CI)

**Canonical documentation**

- [Using uv in GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)
- [setup-uv action](https://github.com/astral-sh/setup-uv)
- [GitHub Actions docs](https://docs.github.com/en/actions)

## Minimal workflow pattern

1. **`actions/checkout`** (pin to a major version the repo trusts, e.g. `v4` or newer per org policy).
2. **`astral-sh/setup-uv`** with a **pinned `uv` version** for reproducibility (`version: "…"` in `with:`).
3. **`uv sync`** from the **`fda-regulations/`** project root using **`--locked`** (per uv’s GitHub guide) and include **`--dev`** when your lockfile separates dev groups.
4. Run checks with **`uv run`**.

Example skeleton (adjust paths and Python pin to match `pyproject.toml`):

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: fda-regulations
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          # Pin a release from https://github.com/astral-sh/uv/releases (Astral docs use explicit pins)
          version: "0.11.4"
          enable-cache: true

      - name: Sync environment
        run: uv sync --locked --all-extras --dev

      - name: Ruff
        run: uv run ruff check . && uv run ruff format --check .

      - name: Pyright
        run: uv run pyright

      - name: Pytest
        run: uv run pytest
```

## Python version

- Prefer a **`.python-version`** or `requires-python` in `pyproject.toml` and use **`uv python install`** or **`actions/setup-python`** with **`python-version-file`** as described in the [uv GitHub guide](https://docs.astral.sh/uv/guides/integration/github/).

## Monorepo note

This repository keeps the uv project under **`fda-regulations/`**. Set **`working-directory:`** on run steps or pass **`uv --directory fda-regulations`** ([uv-packaging](../uv-packaging/SKILL.md)).

## Caching

- Prefer **`enable-cache: true`** on `setup-uv`, or follow uv’s **`UV_CACHE_DIR`** + `actions/cache` pattern from the same guide; run **`uv cache prune --ci`** when recommended.

## Cross-references

- Tool configuration: [ruff-pyright-ci](../ruff-pyright-ci/SKILL.md).
