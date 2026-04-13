"""Pull visible paragraph text from FDA warning letter detail HTML.

Short paragraphs (under ``HEADING_MERGE_THRESHOLD`` characters) are prepended to the
next substantive paragraph so that heading-only ``<p>`` elements ("CGMP Violations",
"Conclusion", etc.) do not become standalone chunks that dominate BM25 for exact-match
queries.  If a short paragraph has no following substantive paragraph, it is emitted
as-is.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

HEADING_MERGE_THRESHOLD: int = 80


def extract_paragraph_texts(html: str) -> list[str]:
    """Return non-empty ``<p>`` texts with heading-merge applied.

    Adjacent short paragraphs are accumulated and prepended (newline-joined) to the
    next paragraph that meets or exceeds ``HEADING_MERGE_THRESHOLD``.
    """
    soup = BeautifulSoup(html, "lxml")
    main = soup.select_one("article#main-content") or soup.select_one("#main-content")
    if main is None:
        return []
    for tag in main.find_all(["script", "style", "noscript"]):
        tag.decompose()

    raw: list[str] = []
    for p in main.find_all("p"):
        t = p.get_text(" ", strip=True)
        if t:
            raw.append(t)

    return _merge_short_paragraphs(raw, HEADING_MERGE_THRESHOLD)


def _merge_short_paragraphs(paragraphs: list[str], threshold: int) -> list[str]:
    """Prepend runs of short paragraphs to the next substantive one."""
    out: list[str] = []
    pending: list[str] = []

    for text in paragraphs:
        if len(text) < threshold:
            pending.append(text)
        else:
            if pending:
                out.append("\n".join([*pending, text]))
                pending.clear()
            else:
                out.append(text)

    out.extend(pending)
    return out
