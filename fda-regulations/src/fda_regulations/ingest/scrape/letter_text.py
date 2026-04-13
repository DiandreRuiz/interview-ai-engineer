"""Strip FDA chrome and return the visible letter body (for preview / chunking input)."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup


def extract_warning_letter_main_text(html: str) -> str:
    """Return plain text inside FDA's main article region (``article#main-content``).

    If the region is missing (unexpected template), returns an empty string.
    """
    soup = BeautifulSoup(html, "lxml")
    main = soup.select_one("article#main-content") or soup.select_one("#main-content")
    if main is None:
        return ""
    for tag in main.find_all(["script", "style", "noscript"]):
        tag.decompose()
    text = main.get_text("\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
