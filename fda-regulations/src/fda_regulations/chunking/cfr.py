"""Extract 21 CFR citation strings from chunk text (cheap regex, not legal parsing).

Stored per chunk as metadata only; retrieval uses paragraph text. Planned uses (e.g. API
citations, boosts) are documented in ``context/plans/implementation-plan.md`` (Next steps).
"""

from __future__ import annotations

import re

# Matches common FDA letter forms: "21 CFR Part 211", "21 CFR 211.42", "21 C.F.R. § 820.30"
_CFR_RE = re.compile(
    r"\b21\s+C\.?F\.?R\.?\s+(?:§\s*|Section\s+|Part\s+)?\d+(?:\.\d+)*\b",
    re.IGNORECASE | re.UNICODE,
)


def extract_cfr_citations(text: str) -> tuple[str, ...]:
    """Return unique citations in document order (case-preserved spans)."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _CFR_RE.finditer(text):
        span = m.group(0).strip()
        key = span.casefold()
        if key not in seen:
            seen.add(key)
            out.append(span)
    return tuple(out)
