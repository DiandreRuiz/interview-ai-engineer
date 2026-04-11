"""Public API for FDA warning letter **scraping** (batch listing + detail fetch).

Reviewers and application code should import from here::

    from fda_regulations.ingest.scrape import run_ingest, extract_warning_letter_main_text

Implementation modules live in this package (see ``ingest/README.md``).
"""

from fda_regulations.config import FDA_WARNING_LETTERS_LISTING_URL

from .letter_text import extract_warning_letter_main_text
from .listing import parse_listing_page
from .main import (
    ListingBatchProgress,
    build_ingest_client,
    iter_letter_list_entries,
    run_ingest,
    run_ingest_new_letters,
)
from .models import IngestResult, LetterListEntry, RawLetterDocument, utc_now

__all__ = [
    "FDA_WARNING_LETTERS_LISTING_URL",
    "IngestResult",
    "ListingBatchProgress",
    "LetterListEntry",
    "RawLetterDocument",
    "build_ingest_client",
    "extract_warning_letter_main_text",
    "iter_letter_list_entries",
    "parse_listing_page",
    "run_ingest",
    "run_ingest_new_letters",
    "utc_now",
]
