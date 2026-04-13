"""Extract 21 CFR citation strings from chunk text via corpus-validated regex.

Two compiled patterns cover the surface forms observed across the full 3,384-letter
warning-letter corpus (short-form ``21 CFR …`` variants **and** the long-form
``Title 21 … Code of Federal Regulations (CFR), Part …`` boilerplate).  Stored per
chunk as metadata only; retrieval uses paragraph text.  Planned uses (e.g. API
citations, boosts) are documented in ``context/plans/implementation-plan.md``
(Next steps).
"""

from __future__ import annotations

import re

# --- Pattern A: short-form (widened) ----------------------------------------
# Handles "21 CFR Part 211", "21 CFR 211.42", "21 C.F.R. § 820.30",
# "21 CFR parts 210", and "21 CFR, parts 210".
_SHORT_CFR = re.compile(
    r"\b21\s+C\.?F\.?R\.?\s*,?\s*(?:§\s*|Section\s+|Parts?\s+)?\d+(?:\.\d+)*\b",
    re.IGNORECASE | re.UNICODE,
)

# --- Pattern B: long-form bridge --------------------------------------------
# "Title 21, Code of Federal Regulations (CFR), Part 820"
# "Title 21 of the Code of Federal Regulations (CFR), parts 210 and 211"
# "Title 21, Code of Federal Regulations (21 CFR) Part 1271"
_LONG_CFR = re.compile(
    r"Title\s+21(?:\s*,\s*|\s+(?:of\s+)?(?:the\s+)?)"
    r"Code\s+of\s+Federal\s+Regulations"
    r"\s*\(\s*(?:21\s+)?CFR\s*\)"
    r"\s*,?\s*(?:Parts?\s+)?[\d]+(?:\.\d+)*\b",
    re.IGNORECASE | re.UNICODE,
)

_PATTERNS: tuple[re.Pattern[str], ...] = (_SHORT_CFR, _LONG_CFR)


def extract_cfr_citations(text: str) -> tuple[str, ...]:
    """Return unique citations in document order (case-preserved spans).

    Runs both short-form and long-form patterns, merges overlapping spans by
    start position, and deduplicates case-insensitively.
    """
    hits: list[tuple[int, str]] = []
    covered_starts: set[int] = set()
    for pattern in _PATTERNS:
        for m in pattern.finditer(text):
            if m.start() not in covered_starts:
                covered_starts.add(m.start())
                hits.append((m.start(), m.group(0).strip()))

    hits.sort(key=lambda t: t[0])

    seen: set[str] = set()
    out: list[str] = []
    for _pos, span in hits:
        key = span.casefold()
        if key not in seen:
            seen.add(key)
            out.append(span)
    return tuple(out)
