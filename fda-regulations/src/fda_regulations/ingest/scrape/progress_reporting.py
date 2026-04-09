"""Rich-based stderr progress for live FDA scraping (TTY only by default)."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from types import TracebackType

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)


def want_show_progress(show_progress: bool | None) -> bool:
    """Resolve whether to show Rich progress: explicit flag, else stderr TTY."""
    if show_progress is False:
        return False
    if show_progress is True:
        return True
    return sys.stderr.isatty()


def _short_id(letter_id: str, *, max_len: int = 52) -> str:
    if len(letter_id) <= max_len:
        return letter_id
    return f"{letter_id[: max_len - 1]}…"


class _RichScrapeProgress:
    """Two-line progress: catalog listing offset vs total, then detail GET progress."""

    def __init__(self, *, incremental: bool, max_letters: int | None) -> None:
        self._incremental = incremental
        self._max_letters = max_letters
        self._cm: Progress | None = None
        self._progress: Progress | None = None
        self._scan_tid: TaskID | None = None
        self._fetch_tid: TaskID | None = None
        self._fetched_new = 0
        self._skipped_existing = 0

    def __enter__(self) -> _RichScrapeProgress:
        self._cm = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=Console(stderr=True),
        )
        self._progress = self._cm.__enter__()
        self._scan_tid = self._progress.add_task("[cyan]Catalog[/]", total=None)
        self._fetch_tid = self._progress.add_task("[green]Detail GETs[/]", total=None)
        self._progress.console.print(
            "\n[bold cyan]FDA warning letters[/bold cyan] · scraping…\n",
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        out: bool | None = None
        if self._cm is not None:
            out = self._cm.__exit__(exc_type, exc_val, exc_tb)
        self._cm = None
        self._progress = None
        return out

    def on_listing_batch(
        self,
        *,
        batch_index: int,
        start: int,
        raw_row_count: int,
        records_filtered: int,
        records_total: int,
    ) -> None:
        if self._progress is None or self._scan_tid is None or self._fetch_tid is None:
            return
        end = start + raw_row_count - 1
        done = min(start + raw_row_count, records_filtered)
        self._progress.update(
            self._scan_tid,
            total=records_filtered,
            completed=done,
            description=(
                f"[cyan]Listing batch {batch_index + 1} · rows {start}–{end} "
                f"of {records_filtered}[/] [dim](recordsTotal={records_total})[/]"
            ),
        )
        if not self._incremental:
            cap = records_filtered
            if self._max_letters is not None:
                cap = min(cap, self._max_letters)
            cur = self._progress.tasks[self._fetch_tid].completed
            self._progress.update(self._fetch_tid, total=cap, completed=cur)

    def on_detail_ok(self, letter_id: str) -> None:
        if self._progress is None or self._fetch_tid is None:
            return
        short = _short_id(letter_id)
        if self._incremental:
            self._fetched_new += 1
            self._progress.update(
                self._fetch_tid,
                description=(
                    f"[green]{self._fetched_new} new HTML fetch(es)[/] · "
                    f"[yellow]{self._skipped_existing} skipped[/] · [dim]{short}[/]"
                ),
            )
            return
        self._progress.advance(self._fetch_tid, 1)
        self._progress.update(
            self._fetch_tid,
            description=f"[green]GET letter[/] [dim]{short}[/]",
        )

    def on_detail_error(self, letter_id: str) -> None:
        if self._progress is None or self._fetch_tid is None:
            return
        short = _short_id(letter_id)
        if self._incremental:
            self._progress.update(
                self._fetch_tid,
                description=(
                    f"[red]HTTP error[/] [dim]{short}[/] · [green]{self._fetched_new} ok[/]"
                ),
            )
            return
        self._progress.update(
            self._fetch_tid,
            description=f"[red]HTTP error[/] [dim]{short}[/]",
        )

    def on_skipped_existing(self) -> None:
        if self._progress is None or self._fetch_tid is None or not self._incremental:
            return
        self._skipped_existing += 1
        self._progress.update(
            self._fetch_tid,
            description=(
                f"[green]{self._fetched_new} new[/] · "
                f"[yellow]{self._skipped_existing} skipped[/] (already in corpus)"
            ),
        )


@contextmanager
def scrape_progress_sink(
    enabled: bool,
    *,
    incremental: bool,
    max_letters: int | None,
) -> Iterator[_RichScrapeProgress | None]:
    if not enabled:
        yield None
        return
    ui = _RichScrapeProgress(incremental=incremental, max_letters=max_letters)
    with ui:
        yield ui
