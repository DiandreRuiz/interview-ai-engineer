"""Primary scrape orchestration: listing pagination and per-letter detail HTML fetch."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator, Set
from typing import TypedDict

import httpx

from fda_regulations.config import Settings

from .datatables_listing import (
    build_datatables_query_params,
    datatables_ajax_request_url,
    decode_datatables_ajax_response,
    extract_view_dom_id,
)
from .models import IngestResult, LetterListEntry, RawLetterDocument, utc_now
from .progress_reporting import scrape_progress_sink


def build_ingest_client(settings: Settings) -> httpx.Client:
    """HTTP client for FDA ingest (timeout, User-Agent, redirects)."""
    timeout = httpx.Timeout(60.0, connect=15.0)
    headers = {"User-Agent": settings.fda_user_agent}
    return httpx.Client(timeout=timeout, headers=headers, follow_redirects=True)


class ListingBatchProgress(TypedDict):
    """Emitted once per DataTables AJAX page (before detail GETs for those rows)."""

    batch_index: int
    start: int
    raw_row_count: int
    records_filtered: int
    records_total: int


def _listing_catalog_tracker() -> tuple[
    Callable[[ListingBatchProgress], None],
    Callable[[], tuple[int | None, int | None, int]],
]:
    """Accumulate DataTables totals for ingest diagnostics (always; not tied to Rich UI)."""
    raw_traversed = 0
    records_filtered: int | None = None
    records_total: int | None = None

    def observe(info: ListingBatchProgress) -> None:
        nonlocal raw_traversed, records_filtered, records_total
        records_filtered = info["records_filtered"]
        records_total = info["records_total"]
        raw_traversed += info["raw_row_count"]

    def snapshot() -> tuple[int | None, int | None, int]:
        return records_filtered, records_total, raw_traversed

    return observe, snapshot


def iter_letter_list_entries(
    client: httpx.Client,
    settings: Settings,
    *,
    max_entries: int | None = None,
    listing_fetch_count: dict[str, int] | None = None,
    on_listing_batch: Callable[[ListingBatchProgress], None] | None = None,
) -> Iterator[tuple[int, LetterListEntry]]:
    """Yield ``(batch_index, entry)`` across DataTables AJAX batches until done or capped.

    Fetches the listing shell page once to obtain ``view_dom_id``, then pages
    ``/datatables/views/ajax`` with ``start`` / ``length``.

    If ``listing_fetch_count`` is provided, increment key ``"n"`` on each listing-related
    HTTP GET (shell + each AJAX page).

    If ``on_listing_batch`` is set, it is invoked after each successful AJAX decode and
    before yielding entries from that page (see :class:`ListingBatchProgress`).
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
        records_total, records_filtered, entries, raw_row_count = decode_datatables_ajax_response(
            response.text,
            page_url=base,
        )

        if raw_row_count == 0:
            break

        if on_listing_batch is not None:
            on_listing_batch(
                {
                    "batch_index": batch_index,
                    "start": start,
                    "raw_row_count": raw_row_count,
                    "records_filtered": records_filtered,
                    "records_total": records_total,
                }
            )

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
    """Discover letters via DataTables AJAX listing, then fetch each detail page HTML.

    Shows Rich progress on stderr (listing offset + detail GET bar).
    """
    max_letters = settings.ingest_max_letters
    if max_letters is not None and max_letters < 1:
        msg = "ingest_max_letters must be >= 1 when set"
        raise ValueError(msg)

    documents: list[RawLetterDocument] = []
    errors: list[str] = []
    rows_seen = 0
    delay = settings.ingest_request_delay_seconds
    listing_stats: dict[str, int] = {"n": 0}
    observe_catalog, catalog_snapshot = _listing_catalog_tracker()

    with scrape_progress_sink(
        incremental=False,
        max_letters=max_letters,
    ) as ui:

        def on_listing_batch(info: ListingBatchProgress) -> None:
            observe_catalog(info)
            ui.on_listing_batch(**info)

        with build_ingest_client(settings) as client:
            for _batch_idx, entry in iter_letter_list_entries(
                client,
                settings,
                max_entries=max_letters,
                listing_fetch_count=listing_stats,
                on_listing_batch=on_listing_batch,
            ):
                rows_seen += 1
                try:
                    documents.append(_fetch_letter_html(client, entry))
                    ui.on_detail_ok(entry.letter_id)
                except httpx.HTTPError as exc:
                    errors.append(f"{entry.letter_id}: {exc!s}")
                    ui.on_detail_error(entry.letter_id)
                if delay > 0:
                    time.sleep(delay)

    rf, rt, raw_trav = catalog_snapshot()
    return IngestResult(
        documents=tuple(documents),
        listing_pages_fetched=listing_stats["n"],
        listing_rows_seen=rows_seen,
        fetch_errors=tuple(errors),
        catalog_records_filtered=rf,
        catalog_records_total=rt,
        listing_raw_rows_traversed=raw_trav,
    )


def run_ingest_new_letters(
    settings: Settings,
    existing_letter_ids: Set[str],
) -> IngestResult:
    """Walk the full warning-letter listing and fetch **only** letters missing from the id set.

    Letters whose ``letter_id`` is already in ``existing_letter_ids`` are skipped.

    Listing pagination and HTTP behavior match :func:`run_ingest` (respects
    ``ingest_max_listing_pages`` / ``ingest_max_letters`` on ``settings``).
    Callers that need to scan the entire catalog for new slugs should pass a
    settings object with both caps unset (``None``).

    Skipped (already-known) rows still increment ``listing_rows_seen``; returned
    ``documents`` contain **newly fetched** letters only.

    Rich progress on stderr matches :func:`run_ingest`.
    """
    max_letters = settings.ingest_max_letters
    if max_letters is not None and max_letters < 1:
        msg = "ingest_max_letters must be >= 1 when set"
        raise ValueError(msg)

    documents: list[RawLetterDocument] = []
    errors: list[str] = []
    rows_seen = 0
    delay = settings.ingest_request_delay_seconds
    listing_stats: dict[str, int] = {"n": 0}
    observe_catalog, catalog_snapshot = _listing_catalog_tracker()

    with scrape_progress_sink(
        incremental=True,
        max_letters=max_letters,
    ) as ui:

        def on_listing_batch(info: ListingBatchProgress) -> None:
            observe_catalog(info)
            ui.on_listing_batch(**info)

        with build_ingest_client(settings) as client:
            for _batch_idx, entry in iter_letter_list_entries(
                client,
                settings,
                max_entries=max_letters,
                listing_fetch_count=listing_stats,
                on_listing_batch=on_listing_batch,
            ):
                rows_seen += 1
                if entry.letter_id in existing_letter_ids:
                    ui.on_skipped_existing()
                    if delay > 0:
                        time.sleep(delay)
                    continue
                try:
                    documents.append(_fetch_letter_html(client, entry))
                    ui.on_detail_ok(entry.letter_id)
                except httpx.HTTPError as exc:
                    errors.append(f"{entry.letter_id}: {exc!s}")
                    ui.on_detail_error(entry.letter_id)
                if delay > 0:
                    time.sleep(delay)

    rf, rt, raw_trav = catalog_snapshot()
    return IngestResult(
        documents=tuple(documents),
        listing_pages_fetched=listing_stats["n"],
        listing_rows_seen=rows_seen,
        fetch_errors=tuple(errors),
        catalog_records_filtered=rf,
        catalog_records_total=rt,
        listing_raw_rows_traversed=raw_trav,
    )
