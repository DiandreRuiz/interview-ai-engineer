"""Pull visible paragraph text from FDA warning letter detail HTML."""

from __future__ import annotations

from bs4 import BeautifulSoup


def extract_paragraph_texts(html: str) -> list[str]:
    """Return non-empty ``<p>`` texts inside ``article#main-content`` (or ``#main-content``)."""
    soup = BeautifulSoup(html, "lxml")
    main = soup.select_one("article#main-content") or soup.select_one("#main-content")
    if main is None:
        return []
    for tag in main.find_all(["script", "style", "noscript"]):
        tag.decompose()

    out: list[str] = []
    for p in main.find_all("p"):
        t = p.get_text(" ", strip=True)
        if t:
            out.append(t)
    return out
