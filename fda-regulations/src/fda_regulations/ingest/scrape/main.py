"""Primary scrape orchestration: listing pagination and per-letter detail HTML fetch."""

from __future__ import annotations

import time
from collections.abc import Iterator

import httpx

from fda_regulations.config import Settings

from .client import build_ingest_client
from .listing import parse_listing_page
from .models import IngestResult, LetterListEntry, RawLetterDocument, utc_now


def _listing_page_url(base: str, page: int) -> str:
    base = base.rstrip("/")
    return f"{base}?page={page}"


def iter_letter_list_entries(
    client: httpx.Client,
    settings: Settings,
    *,
    max_entries: int | None = None,
    listing_fetch_count: dict[str, int] | None = None,
) -> Iterator[tuple[int, LetterListEntry]]:
    """Yield ``(page_index, entry)`` across listing pages until empty, caps, or ``max_entries``.

    If ``listing_fetch_count`` is provided, increment key ``"n"`` on each listing GET.
    """
    base = str(settings.ingest_listing_base_url)
    max_pages = settings.ingest_max_listing_pages
    delay = settings.ingest_request_delay_seconds
    if max_pages is not None and max_pages < 1:
        msg = "ingest_max_listing_pages must be >= 1 when set"
        raise ValueError(msg)

    seen_ids: set[str] = set()
    emitted = 0
    page = 0
    while max_pages is None or page < max_pages:
        url = _listing_page_url(base, page)
        response = client.get(url)
        if listing_fetch_count is not None:
            listing_fetch_count["n"] += 1
        response.raise_for_status()
        entries = parse_listing_page(response.text, page_url=url)
        if not entries:
            break
        for entry in entries:
            if entry.letter_id in seen_ids:
                continue
            seen_ids.add(entry.letter_id)
            yield page, entry
            emitted += 1
            if max_entries is not None and emitted >= max_entries:
                return
        page += 1
        if delay > 0:
            time.sleep(delay)


def _fetch_letter_html(client: httpx.Client, entry: LetterListEntry) -> RawLetterDocument:
    response = client.get(str(entry.url))
    response.raise_for_status()
    return RawLetterDocument(
        letter_id=entry.letter_id,
        url=entry.url,
        html=response.text,
        fetched_at_utc=utc_now(),
        company_name=entry.company_name,
        posted_date=entry.posted_date,
        letter_issue_date=entry.letter_issue_date,
    )


def run_ingest(settings: Settings) -> IngestResult:
    """Discover letters via paginated listing, then fetch each detail page HTML."""
    max_letters = settings.ingest_max_letters
    if max_letters is not None and max_letters < 1:
        msg = "ingest_max_letters must be >= 1 when set"
        raise ValueError(msg)

    documents: list[RawLetterDocument] = []
    errors: list[str] = []
    rows_seen = 0
    delay = settings.ingest_request_delay_seconds
    listing_stats: dict[str, int] = {"n": 0}

    with build_ingest_client(settings) as client:
        for _page_idx, entry in iter_letter_list_entries(
            client,
            settings,
            max_entries=max_letters,
            listing_fetch_count=listing_stats,
        ):
            rows_seen += 1
            try:
                documents.append(_fetch_letter_html(client, entry))
            except httpx.HTTPError as exc:
                errors.append(f"{entry.letter_id}: {exc!s}")
            if delay > 0:
                time.sleep(delay)

    return IngestResult(
        documents=tuple(documents),
        listing_pages_fetched=listing_stats["n"],
        listing_rows_seen=rows_seen,
        fetch_errors=tuple(errors),
    )
