"""Parse FDA warning letter listing HTML into ``LetterListEntry`` rows."""

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .models import LetterListEntry


def _is_detail_href(href: str) -> bool:
    if "/warning-letters/" not in href:
        return False
    path = urlparse(href).path.rstrip("/")
    if path.endswith("/warning-letters"):
        return False
    tail = path.split("/warning-letters/")[-1]
    if not tail:
        return False
    return not tail.lower().startswith("about")


def _slug_from_href(href: str) -> str:
    path = urlparse(href).path.rstrip("/")
    return path.split("/warning-letters/")[-1]


def parse_listing_page(html: str, *, page_url: str) -> list[LetterListEntry]:
    """Extract letter rows from one listing page (FDA table: posted, issue, company link, …)."""
    soup = BeautifulSoup(html, "lxml")
    rows: list[LetterListEntry] = []
    for tr in soup.select("table tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 3:
            continue
        posted = tds[0].get_text(strip=True)
        issue = tds[1].get_text(strip=True)
        link = tds[2].find("a", href=True)
        if link is None:
            continue
        href = str(link.get("href", "")).strip()
        if not _is_detail_href(href):
            continue
        abs_url = urljoin(page_url, href)
        slug = _slug_from_href(href)
        company = link.get_text(strip=True) or None
        rows.append(
            LetterListEntry(
                letter_id=slug,
                url=abs_url,
                company_name=company,
                posted_date=posted or None,
                letter_issue_date=issue or None,
            )
        )
    return rows
