"""CLI: scrape FDA warning letters (listing pagination + detail HTML fetch)."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from fda_regulations.cli.ingest_rich_summary import (
    configure_rich_cli_logging,
    ingest_console_stdout,
    print_ingest_completion_report,
    print_run_banner,
)
from fda_regulations.config import Settings
from fda_regulations.ingest.corpus import write_corpus_jsonl
from fda_regulations.ingest.scrape import extract_warning_letter_main_text, run_ingest


def main() -> None:
    configure_rich_cli_logging()
    parser = argparse.ArgumentParser(
        description="Scrape FDA warning letters: DataTables listing + per-letter HTML GETs.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Override INGEST_MAX_LISTING_PAGES (cap DataTables AJAX batches after shell GET).",
    )
    parser.add_argument(
        "--max-letters",
        type=int,
        default=None,
        help="Override INGEST_MAX_LETTERS (max letters to fetch after discovery).",
    )
    parser.add_argument(
        "--preview-dir",
        type=Path,
        default=None,
        help="Write extracted main text per letter as <letter_id>.txt (article#main-content).",
    )
    parser.add_argument(
        "--write-corpus",
        action="store_true",
        help=(
            "Write letters.jsonl and corpus_manifest.json under the corpus directory "
            "(INGEST_CORPUS_DIR or ARTIFACT_ROOT/corpus)."
        ),
    )
    args = parser.parse_args()
    settings = Settings()
    overrides: dict[str, int] = {}
    if args.max_pages is not None:
        overrides["ingest_max_listing_pages"] = args.max_pages
    if args.max_letters is not None:
        overrides["ingest_max_letters"] = args.max_letters
    if overrides:
        settings = settings.model_copy(update=overrides)

    out = ingest_console_stdout()
    print_run_banner(out, "FDA scrape", "Live listing + detail GETs · stderr = Rich progress")

    result = run_ingest(settings)
    logging.info("Fetched %s letter document(s).", len(result.documents))
    logging.info("Listing HTTP GETs (shell + DataTables): %s", result.listing_pages_fetched)
    logging.info("Listing rows iterated: %s", result.listing_rows_seen)
    if result.fetch_errors:
        first = result.fetch_errors[0]
        logging.warning("%s fetch error(s), e.g. %s", len(result.fetch_errors), first)

    print_ingest_completion_report(out, result, run_label="fda-scrape")

    if args.write_corpus:
        stats = write_corpus_jsonl(result.documents, settings.resolved_ingest_corpus_dir)
        logging.info(
            "Wrote corpus: %s (%s document(s))",
            stats.letters_jsonl,
            stats.documents_written,
        )

    if args.preview_dir is not None:
        args.preview_dir.mkdir(parents=True, exist_ok=True)
        for doc in result.documents:
            body = extract_warning_letter_main_text(doc.html)
            out_path = args.preview_dir / f"{doc.letter_id}.txt"
            out_path.write_text(body, encoding="utf-8")
            logging.info("Wrote %s (%s chars main text)", out_path.name, len(body))


if __name__ == "__main__":
    main()
