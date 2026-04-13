#!/usr/bin/env python3
"""Thin wrapper — implementation lives in ``fda_regulations.cli.rehydrate``.

Run from ``fda-regulations/``::

    uv run fda-rehydrate --artifact-root ./artifacts

Equivalent::

    uv run python scripts/rehydrate_warning_letters.py --artifact-root ./artifacts
"""

from fda_regulations.cli.rehydrate import main

if __name__ == "__main__":
    main()
