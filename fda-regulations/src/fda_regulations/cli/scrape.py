"""CLI: scrape FDA warning letters (listing pagination + detail HTML fetch)."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from fda_regulations.config import Settings
from fda_regulations.ingest.scrape import extract_warning_letter_main_text, run_ingest


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Scrape FDA warning letters: paginated listing + per-letter HTML GETs.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Override INGEST_MAX_LISTING_PAGES (max listing pages to scan).",
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
    args = parser.parse_args()
    settings = Settings()
    overrides: dict[str, int] = {}
    if args.max_pages is not None:
        overrides["ingest_max_listing_pages"] = args.max_pages
    if args.max_letters is not None:
        overrides["ingest_max_letters"] = args.max_letters
    if overrides:
        settings = settings.model_copy(update=overrides)

    result = run_ingest(settings)
    logging.info("Fetched %s letter document(s).", len(result.documents))
    logging.info("Listing pages fetched: %s", result.listing_pages_fetched)
    logging.info("Listing rows iterated: %s", result.listing_rows_seen)
    if result.fetch_errors:
        first = result.fetch_errors[0]
        logging.warning("%s fetch error(s), e.g. %s", len(result.fetch_errors), first)

    if args.preview_dir is not None:
        args.preview_dir.mkdir(parents=True, exist_ok=True)
        for doc in result.documents:
            body = extract_warning_letter_main_text(doc.html)
            out_path = args.preview_dir / f"{doc.letter_id}.txt"
            out_path.write_text(body, encoding="utf-8")
            logging.info("Wrote %s (%s chars main text)", out_path.name, len(body))


if __name__ == "__main__":
    main()
