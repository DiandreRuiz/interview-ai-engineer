"""FDA warning letter discovery via Drupal DataTables AJAX (Solr-backed view).

The public listing page loads rows from ``/datatables/views/ajax`` using ``start`` /
``length`` pagination—not reliable ``?page=`` on the document URL. We fetch the shell
page once to read ``view_dom_id`` from embedded JSON, then page the AJAX endpoint.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urlencode, urljoin, urlparse

from bs4 import BeautifulSoup

from fda_regulations.ingest.scrape.listing import _is_detail_href, _slug_from_href
from fda_regulations.ingest.scrape.models import LetterListEntry

_VIEW_DOM_ID_RE = re.compile(r'"view_dom_id"\s*:\s*"([^"]+)"')

# Mirrors the FDA warning-letters view wiring (see Network tab on the listing page).
_DATATABLES_AJAX_PATH = "/datatables/views/ajax"
_VIEW_BASE_PATH = (
    "inspections-compliance-enforcement-and-criminal-investigations/"
    "compliance-actions-and-activities/warning-letters/datatables-data"
)
_VIEW_DISPLAY_ID = "warning_letter_solr_block"
_VIEW_NAME = "warning_letter_solr_index"
_VIEW_PATH = (
    "/inspections-compliance-enforcement-and-criminal-investigations/"
    "compliance-actions-and-activities/warning-letters"
)
_NUM_COLUMNS = 8


def extract_view_dom_id(listing_html: str) -> str | None:
    """Parse ``view_dom_id`` from the warning-letters shell HTML (Drupal settings JSON)."""
    m = _VIEW_DOM_ID_RE.search(listing_html)
    return m.group(1) if m else None


def datatables_ajax_base_url(listing_base_url: str) -> str:
    """``https://host/datatables/views/ajax`` for the same host as ``listing_base_url``."""
    parsed = urlparse(listing_base_url)
    if not parsed.scheme or not parsed.netloc:
        msg = f"ingest_listing_base_url must be absolute with scheme and host: {listing_base_url!r}"
        raise ValueError(msg)
    return f"{parsed.scheme}://{parsed.netloc}{_DATATABLES_AJAX_PATH}"


def build_datatables_query_params(
    view_dom_id: str,
    *,
    start: int,
    length: int,
    draw: int,
) -> dict[str, str]:
    """Build flat query parameters for a single DataTables AJAX GET (FDA / Drupal)."""
    params: dict[str, str] = {
        "search_api_fulltext": "",
        "search_api_fulltext_issuing_office": "",
        "field_letter_issue_datetime": "All",
        "field_change_date_closeout_letter": "",
        "field_change_date_response_letter": "",
        "field_change_date_2": "All",
        "field_letter_issue_datetime_2": "",
        "draw": str(draw),
        "start": str(start),
        "length": str(length),
        "search[value]": "",
        "search[regex]": "false",
        "_drupal_ajax": "1",
        "_wrapper_format": "drupal_ajax",
        "pager_element": "0",
        "view_args": "",
        "view_base_path": _VIEW_BASE_PATH,
        "view_display_id": _VIEW_DISPLAY_ID,
        "view_dom_id": view_dom_id,
        "view_name": _VIEW_NAME,
        "view_path": _VIEW_PATH,
    }
    for i in range(_NUM_COLUMNS):
        params[f"columns[{i}][data]"] = str(i)
        params[f"columns[{i}][name]"] = ""
        params[f"columns[{i}][searchable]"] = "true"
        params[f"columns[{i}][orderable]"] = "false" if i == 7 else "true"
        params[f"columns[{i}][search][value]"] = ""
        params[f"columns[{i}][search][regex]"] = "false"
    return params


def datatables_ajax_request_url(listing_base_url: str, params: dict[str, str]) -> str:
    base = datatables_ajax_base_url(listing_base_url)
    return f"{base}?{urlencode(params)}"


def _parse_date_cell(html_frag: str) -> str | None:
    soup = BeautifulSoup(html_frag, "lxml")
    time_el = soup.find("time")
    if time_el is not None:
        text = time_el.get_text(strip=True)
        if text:
            return text
    text = soup.get_text(" ", strip=True)
    return text or None


def parse_datatables_row_to_entry(row: object, *, page_url: str) -> LetterListEntry | None:
    """Map one AJAX ``data`` row (list of HTML cell strings) to a ``LetterListEntry``."""
    if not isinstance(row, list) or len(row) < 3:
        return None
    company_cell = row[2]
    if not isinstance(company_cell, str):
        return None
    soup = BeautifulSoup(company_cell, "lxml")
    link = soup.find("a", href=True)
    if link is None:
        return None
    href = str(link.get("href", "")).strip()
    if not _is_detail_href(href):
        return None

    abs_url = urljoin(page_url, href)
    slug = _slug_from_href(href)
    company = link.get_text(strip=True) or None
    posted = _parse_date_cell(row[0]) if isinstance(row[0], str) else None
    issue = _parse_date_cell(row[1]) if isinstance(row[1], str) else None
    return LetterListEntry(
        letter_id=slug,
        url=abs_url,
        company_name=company,
        posted_date=posted,
        letter_issue_date=issue,
    )


def parse_datatables_ajax_json(
    payload: object,
    *,
    page_url: str,
) -> tuple[int, int, list[LetterListEntry], int]:
    """Parse DataTables JSON body.

    Returns ``(records_total, records_filtered, entries, raw_row_count)``.
    ``raw_row_count`` is ``len(data)`` from the payload—use it to advance ``start``,
    even when some rows fail to parse into ``LetterListEntry``.
    """
    if not isinstance(payload, dict):
        msg = f"Expected JSON object from DataTables AJAX, got {type(payload).__name__}"
        raise ValueError(msg)
    try:
        records_total = int(payload["recordsTotal"])
        records_filtered = int(payload["recordsFiltered"])
    except (KeyError, TypeError, ValueError) as exc:
        msg = "DataTables JSON missing or invalid recordsTotal/recordsFiltered"
        raise ValueError(msg) from exc
    raw_rows = payload.get("data")
    if raw_rows is None:
        msg = "DataTables JSON missing data key"
        raise ValueError(msg)
    if not isinstance(raw_rows, list):
        msg = f"DataTables data must be a list, got {type(raw_rows).__name__}"
        raise ValueError(msg)
    entries: list[LetterListEntry] = []
    for row in raw_rows:
        entry = parse_datatables_row_to_entry(row, page_url=page_url)
        if entry is not None:
            entries.append(entry)
    return records_total, records_filtered, entries, len(raw_rows)


def decode_datatables_ajax_response(
    text: str,
    *,
    page_url: str,
) -> tuple[int, int, list[LetterListEntry], int]:
    """Parse HTTP response text as JSON and extract listing entries."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        msg = "DataTables AJAX response is not valid JSON"
        raise ValueError(msg) from exc
    return parse_datatables_ajax_json(payload, page_url=page_url)
