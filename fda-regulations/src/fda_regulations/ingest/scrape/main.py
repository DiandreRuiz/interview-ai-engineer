"""Primary scrape orchestration: listing pagination and per-letter detail HTML fetch."""

from __future__ import annotations

import time
from collections.abc import Iterator

import httpx

from fda_regulations.config import Settings

from .client import build_ingest_client
from .datatables_listing import (
    build_datatables_query_params,
    datatables_ajax_request_url,
    decode_datatables_ajax_response,
    extract_view_dom_id,
)
from .models import IngestResult, LetterListEntry, RawLetterDocument, utc_now


def iter_letter_list_entries(
    client: httpx.Client,
    settings: Settings,
    *,
    max_entries: int | None = None,
    listing_fetch_count: dict[str, int] | None = None,
) -> Iterator[tuple[int, LetterListEntry]]:
    """Yield ``(batch_index, entry)`` across DataTables AJAX batches until done or capped.

    Fetches the listing shell page once to obtain ``view_dom_id``, then pages
    ``/datatables/views/ajax`` with ``start`` / ``length``.

    If ``listing_fetch_count`` is provided, increment key ``"n"`` on each listing-related
    HTTP GET (shell + each AJAX page).
    """
    base = str(settings.ingest_listing_base_url).rstrip("/")
    max_batches = settings.ingest_max_listing_pages
    batch_size = settings.ingest_listing_batch_size
    delay = settings.ingest_request_delay_seconds
    if max_batches is not None and max_batches < 1:
        msg = "ingest_max_listing_pages must be >= 1 when set"
        raise ValueError(msg)

    shell = client.get(base)
    if listing_fetch_count is not None:
        listing_fetch_count["n"] += 1
    shell.raise_for_status()
    view_dom_id = extract_view_dom_id(shell.text)
    if view_dom_id is None:
        msg = (
            "Could not find view_dom_id in listing HTML; FDA template may have changed. "
            f"URL: {base}"
        )
        raise ValueError(msg)

    seen_ids: set[str] = set()
    emitted = 0
    start = 0
    batch_index = 0

    while max_batches is None or batch_index < max_batches:
        draw = batch_index + 1
        params = build_datatables_query_params(
            view_dom_id,
            start=start,
            length=batch_size,
            draw=draw,
        )
        ajax_url = datatables_ajax_request_url(base, params)
        response = client.get(ajax_url)
        if listing_fetch_count is not None:
            listing_fetch_count["n"] += 1
        response.raise_for_status()
        _records_total, records_filtered, entries, raw_row_count = decode_datatables_ajax_response(
            response.text,
            page_url=base,
        )

        if raw_row_count == 0:
            break

        for entry in entries:
            if entry.letter_id in seen_ids:
                continue
            seen_ids.add(entry.letter_id)
            yield batch_index, entry
            emitted += 1
            if max_entries is not None and emitted >= max_entries:
                return

        start += raw_row_count
        if start >= records_filtered:
            break
        if raw_row_count < batch_size:
            break

        batch_index += 1
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
    """Discover letters via DataTables AJAX listing, then fetch each detail page HTML."""
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
        for _batch_idx, entry in iter_letter_list_entries(
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
