#!/usr/bin/env python3
"""Incremental FDA warning-letter ingest: fetch listing, pull only **new** letter_ids, merge corpus, rebuild index.

Run from the ``fda-regulations/`` project root (default for ``uv``) so ``.env`` loads::

    cd fda-regulations
    uv run python scripts/rehydrate_warning_letters.py --artifact-root ./artifacts

Cron example (weekly)::

    0 3 * * 1 cd /path/to/repo/fda-regulations && /path/to/uv run python scripts/rehydrate_warning_letters.py --artifact-root ./artifacts >> /var/log/fda-rehydrate.log 2>&1

This script always **re-embeds the full chunk set** after any new letters (same contract as
``fda-build-index``): BM25 is rebuilt at API load time from ``chunks.jsonl``.

**Next steps (interview):** today the source of truth for "what we already have" is local
``letters.jsonl``. A production job would list object keys in **S3/GCS** (or a manifest in the
object store), stream-merge new HTML into the canonical store, then trigger index rebuild on a
worker with GPU/CPU budget—or incremental vector append if the store supports it. The same
``run_ingest_new_letters`` + merge pattern applies; only the I/O layer changes.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from fda_regulations.chunk_pipeline import raw_letters_to_chunks
from fda_regulations.config import Settings
from fda_regulations.index.build import build_hybrid_index
from fda_regulations.ingest.corpus import (
    CORPUS_LETTERS_JSONL,
    CORPUS_MANIFEST_NAME,
    iter_corpus_letters,
    write_corpus_jsonl,
)
from fda_regulations.ingest.scrape import run_ingest_new_letters
from fda_regulations.ingest.scrape.models import RawLetterDocument
from fda_regulations.reporting import write_phase1_ingest_report


def _fda_project_root() -> Path:
    """Directory containing ``pyproject.toml`` (``fda-regulations/``)."""
    return Path(__file__).resolve().parent.parent


def _load_corpus_state(corpus_dir: Path) -> tuple[list[RawLetterDocument], set[str]]:
    manifest = corpus_dir / CORPUS_MANIFEST_NAME
    jsonl = corpus_dir / CORPUS_LETTERS_JSONL
    if not manifest.is_file() or not jsonl.is_file():
        return [], set()
    docs = list(iter_corpus_letters(corpus_dir))
    return docs, {d.letter_id for d in docs}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description=(
            "Re-hydrate local corpus: full listing scan, fetch only letters missing from "
            "letters.jsonl, rewrite corpus + rebuild hybrid index."
        ),
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=None,
        help="Index output directory (default: ARTIFACT_ROOT from settings).",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=None,
        help="Corpus directory with letters.jsonl (default: resolved INGEST_CORPUS_DIR).",
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default=None,
        help="Override INDEX_EMBEDDING_MODEL for this rebuild.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Optional path for phase-1 markdown report (same format as fda-build-index).",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable Rich scrape progress on stderr during listing + new-letter fetches.",
    )
    args = parser.parse_args()

    fda_root = _fda_project_root()
    cwd = Path.cwd().resolve()
    if not (fda_root / "pyproject.toml").is_file():
        logging.error("Could not find fda-regulations project root (pyproject.toml); aborting.")
        raise SystemExit(1)
    if cwd != fda_root.resolve():
        logging.warning(
            "Current directory is not fda-regulations/; .env and default paths may be wrong. "
            "Prefer: cd %s && uv run python scripts/rehydrate_warning_letters.py …",
            fda_root,
        )

    settings = Settings()
    artifact_root = (
        args.artifact_root.expanduser().resolve()
        if args.artifact_root is not None
        else settings.artifact_root.expanduser().resolve()
    )
    corpus_dir = (
        args.corpus_dir.expanduser().resolve()
        if args.corpus_dir is not None
        else settings.resolved_ingest_corpus_dir
    )
    model_id = args.embedding_model or settings.index_embedding_model

    ingest_settings = settings.model_copy(
        update={
            "ingest_max_listing_pages": None,
            "ingest_max_letters": None,
        },
    )

    existing_docs, existing_ids = _load_corpus_state(corpus_dir)
    logging.info(
        "Corpus %s: %s letter(s) on disk.",
        corpus_dir,
        len(existing_docs),
    )

    result = run_ingest_new_letters(
        ingest_settings,
        existing_ids,
        show_progress=False if args.no_progress else None,
    )
    logging.info(
        "Listing GETs (shell + DataTables): %s; rows seen: %s; new documents: %s",
        result.listing_pages_fetched,
        result.listing_rows_seen,
        len(result.documents),
    )
    if result.fetch_errors:
        logging.warning(
            "%s letter fetch error(s), e.g. %s", len(result.fetch_errors), result.fetch_errors[0]
        )

    if not result.documents:
        logging.info("No new letters; leaving corpus and index unchanged.")
        return

    merged: list[RawLetterDocument] = existing_docs + list(result.documents)
    write_corpus_jsonl(merged, corpus_dir, source="fda-rehydrate")
    logging.info("Wrote corpus with %s letter(s).", len(merged))

    chunks = raw_letters_to_chunks(merged)
    logging.info("Built %s chunk(s).", len(chunks))

    manifest = build_hybrid_index(artifact_root, chunks, embedding_model_id=model_id)
    logging.info(
        "Wrote hybrid index under %s (%s chunks, model=%s).",
        artifact_root,
        manifest.chunk_count,
        manifest.embedding_model_id,
    )

    if args.report is not None:
        with_cfr = sum(1 for c in chunks if len(c.cfr_citations) > 0)
        write_phase1_ingest_report(
            args.report,
            letter_count=len(merged),
            chunk_count=len(chunks),
            chunks_with_cfr=with_cfr,
            embedding_model_id=model_id,
            artifact_root=artifact_root,
            corpus_dir=corpus_dir,
        )
        logging.info("Wrote report %s", args.report)


if __name__ == "__main__":
    main()
