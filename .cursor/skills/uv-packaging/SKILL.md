---
name: uv-packaging
description: Guides use of Astral uv for Python projects—sync, lock, add, run, Python versions, pip compatibility, and nested project roots. Use when managing dependencies, writing README run instructions, CI setup, or when the user mentions uv, uv.lock, pyproject.toml, or virtualenv for this repo.
---

# uv — usage and practices

**Canonical documentation:** [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)  
**CLI reference:** [https://docs.astral.sh/uv/reference/cli/](https://docs.astral.sh/uv/reference/cli/)

uv is Astral’s Python package and project manager (Rust); it replaces much of pip, pip-tools, virtualenv, and common Poetry/Rye-style flows. It shares maintainers with Ruff.

## Installation

- **Recommended (macOS/Linux):** `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows:** PowerShell one-liner on the [installation page](https://docs.astral.sh/uv/getting-started/installation/)
- Alternatives: `pip install uv`, Homebrew, etc.

## Project workflow (`pyproject.toml` + `uv.lock`)

| Command | Purpose |
|--------|---------|
| **`uv sync`** | Create/update `.venv` and install exactly what the **lockfile** resolves (reproducible). Prefer this after clone or when `uv.lock` changes. |
| **`uv lock`** | Resolve dependencies and **write/update `uv.lock`** (run after changing deps in `pyproject.toml` or when bumping versions intentionally). |
| **`uv add <pkg>`** | Add a runtime dependency; updates `pyproject.toml` and lockfile. Use **`uv add --dev <pkg>`** (or group flags per docs) for dev/test tools. |
| **`uv remove <pkg>`** | Remove dependency; refresh lockfile. |
| **`uv run <cmd>`** | Run a command inside the project environment (uv ensures sync as needed). Example: `uv run pytest`, `uv run python -m mypkg`. |
| **`uv init`** | Scaffold a new project (not needed if `pyproject.toml` already exists). |

**Best practices**

- **Commit `uv.lock`** for applications and takehomes so installs are reproducible.
- For **fda-regulations**, document: `cd fda-regulations && uv sync` (see “This repo” below).
- In **CI**, use `uv sync --frozen` (or current recommended frozen flag from docs) so lockfile mismatches fail fast.

## This repo: `fda-regulations/` as the uv project root

The Modicus assignment uses the **`fda-regulations/`** folder as the `uv` project. **pytest, ruff, pyright, and respx** are listed in **`[project] dependencies`** (not a separate dev group). **Build backend:** **Hatchling** with a **`src/`** layout. **Local setup:** **`cp .env.example .env`** then **`uv sync`** — **`.env`** sets **`PYTHONPATH=src`** so **`uv run`** imports the package reliably (some **macOS** Python builds skip UF_HIDDEN **`.pth`** files; see [cpython#148121](https://github.com/python/cpython/issues/148121)). **pytest** uses **`pythonpath = ["src"]`** so CI does not need `.env`.

Either:

```bash
cd fda-regulations
uv sync
uv run python -m ...
```

or from the **repository root**:

```bash
uv --directory fda-regulations sync
uv --directory fda-regulations run pytest
```

Use **`--directory`** when scripts or docs run uv without changing cwd; some tools still expect cwd inside the package—match what pytest/ruff expect and document it.

## Python versions

- Declare **`requires-python`** in `pyproject.toml` (this project: 3.13 per assignment).
- **`uv python install 3.13`** — install a managed interpreter.
- **`uv python pin 3.13`** — write **`.python-version`** in the project directory for consistent selection.
- **`uv venv --python 3.13`** — create `.venv` with a specific version.

See [Installing Python](https://docs.astral.sh/uv/guides/install-python/).

## Pip-compatible surface (`uv pip …`)

For legacy workflows or quick experiments:

- **`uv venv`** — create a virtual environment.
- **`uv pip install` / `uv pip sync`** — pip-like installs (see [pip interface](https://docs.astral.sh/uv/pip/)).
- **`uv pip compile`** — lock-style `requirements.txt` generation.

Prefer **`uv sync` / `uv add`** for first-class **projects** with `pyproject.toml`.

## Tools and one-off CLIs

- **`uvx <tool>`** (alias for **`uv tool run`**) — run a tool in an **ephemeral** env (similar to pipx for a single invocation).
- **`uv tool install <pkg>`** — install a CLI onto PATH for repeated use.

See [Tools guide](https://docs.astral.sh/uv/guides/tools/).

## Scripts with dependencies

- **`uv run script.py`** can use a project env or [inline script metadata](https://docs.astral.sh/uv/guides/scripts/) for single-file deps.
- **`uv add --script script.py requests`** — inject PEP 723-style metadata for that script.

## Workspaces and packaging

- **Workspaces:** multi-package repos (Cargo-style); see [Workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/).
- **Build/publish:** [Packaging guide](https://docs.astral.sh/uv/guides/package/) for `uv build` / publish flows when relevant.

## When docs drift

uv evolves quickly—if a flag or subcommand fails, check the [CLI reference](https://docs.astral.sh/uv/reference/cli/) and update **`context/plans/implementation-plan.md`** or **`fda-regulations/README.md`** when project commands change.

## Related project skills

For Docker, GitHub Actions with uv, and the retrieval stack, see **`docker-desktop-python`** and **`github-actions-uv-python`** under `.cursor/skills/`.
