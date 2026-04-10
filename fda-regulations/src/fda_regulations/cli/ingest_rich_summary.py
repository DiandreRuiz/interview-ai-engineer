"""Rich (stdout) banners and completion reports for long-running ingest CLIs."""

from __future__ import annotations

import logging
import sys

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from fda_regulations.ingest.scrape.models import IngestResult


def configure_rich_cli_logging() -> None:
    """Route stdlib logging through Rich (stderr). Safe when stderr is not a TTY."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
        force=True,
    )


def ingest_console_stdout() -> Console:
    """Console writing to stdout (step banners and final reports)."""
    return Console(
        file=sys.stdout,
        force_terminal=not sys.stdout.isatty(),
    )


def print_run_banner(console: Console, title: str, subtitle: str | None = None) -> None:
    sub = f"\n[dim]{subtitle}[/dim]" if subtitle else ""
    console.print(
        Panel.fit(
            f"[bold]{title}[/]{sub}",
            border_style="cyan",
        )
    )


def print_step(
    console: Console,
    step: int,
    total: int,
    emoji: str,
    message: str,
) -> None:
    console.print(f"{emoji} [bold]Step {step}/{total}[/] {message}")


def print_ingest_completion_report(
    console: Console,
    result: IngestResult,
    *,
    run_label: str,
    local_letters_before: int | None = None,
    local_letters_after: int | None = None,
) -> None:
    """Table + interpretation hints after scrape / rehydrate discovery."""
    rf = result.catalog_records_filtered
    rt = result.catalog_records_total
    raw_trav = result.listing_raw_rows_traversed

    table = Table(title=f"📋 {run_label} — summary", show_header=True, header_style="bold")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    table.add_row("Listing HTTP GETs (shell + DataTables)", str(result.listing_pages_fetched))
    table.add_row("Listing rows iterated (parsed slugs yielded)", str(result.listing_rows_seen))
    if rf is not None:
        table.add_row("FDA recordsFiltered (catalog total)", str(rf))
    if rt is not None:
        table.add_row("FDA recordsTotal", str(rt))
    if raw_trav is not None:
        table.add_row("Raw DataTables rows consumed (sum of page sizes)", str(raw_trav))

    table.add_row("Letter HTML documents returned", str(len(result.documents)))
    table.add_row("Detail fetch errors", str(len(result.fetch_errors)))

    if local_letters_before is not None:
        table.add_row("Local corpus letters (before)", str(local_letters_before))
    if local_letters_after is not None:
        table.add_row("Local corpus letters (after)", str(local_letters_after))

    console.print()
    console.print(table)

    notes: list[str] = []
    if rf is not None and raw_trav is not None and raw_trav != rf:
        notes.append(
            "[yellow]⚠ Raw rows traversed ≠ recordsFiltered — listing pagination may have "
            "stopped early or counts desynced; re-run or inspect logs.[/]"
        )
    if rf is not None and result.listing_rows_seen < rf:
        diff = rf - result.listing_rows_seen
        notes.append(
            f"[dim]ℹ️  {diff} catalog row(s) not yielded as unique slugs (parse skips, duplicate "
            f"slugs in listing, or rows without a detail link we accept).[/]"
        )
    if result.fetch_errors:
        notes.append(
            f"[red]✖ {len(result.fetch_errors)} detail URL(s) failed HTTP — those letters are not "
            f"in this run’s documents; re-run to retry.[/]"
        )
    else:
        notes.append("[green]✓ No detail-fetch HTTP errors in this run.[/]")

    if notes:
        console.print()
        for line in notes:
            console.print(line)

    console.print()
