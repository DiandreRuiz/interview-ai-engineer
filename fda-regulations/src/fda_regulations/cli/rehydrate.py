"""Incremental warning-letter rehydrate (listing scan, fetch new HTML, merge corpus, rebuild index).

Prefer ``uv run fda-rehydrate`` from ``fda-regulations/`` so the installed package resolves;
``scripts/rehydrate_warning_letters.py`` is a thin wrapper for the same entry point.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from rich.panel import Panel

from fda_regulations.chunking import raw_letters_to_chunks
from fda_regulations.cli.ingest_rich_summary import (
    configure_rich_cli_logging,
    ingest_console_stdout,
    print_ingest_completion_report,
    print_run_banner,
    print_step,
)
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

_STEPS_TOTAL = 5


def _fda_project_root() -> Path:
    """``fda-regulations/`` directory (contains ``pyproject.toml``)."""
    # src/fda_regulations/cli/rehydrate.py -> …/fda-regulations
    return Path(__file__).resolve().parent.parent.parent.parent


def _load_corpus_state(corpus_dir: Path) -> tuple[list[RawLetterDocument], set[str]]:
    manifest = corpus_dir / CORPUS_MANIFEST_NAME
    jsonl = corpus_dir / CORPUS_LETTERS_JSONL
    if not manifest.is_file() or not jsonl.is_file():
        return [], set()
    docs = list(iter_corpus_letters(corpus_dir))
    return docs, {d.letter_id for d in docs}


def main() -> None:
    configure_rich_cli_logging()
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
    args = parser.parse_args()

    out = ingest_console_stdout()
    print_run_banner(
        out,
        "Rehydrate warning letters",
        "Incremental FDA ingest · stdout = milestones · stderr = Rich logs + progress",
    )

    fda_root = _fda_project_root()
    cwd = Path.cwd().resolve()
    if not (fda_root / "pyproject.toml").is_file():
        logging.error("Could not find fda-regulations project root (pyproject.toml); aborting.")
        raise SystemExit(1)
    if cwd != fda_root.resolve():
        logging.warning(
            "Current directory is not fda-regulations/; .env and default paths may be wrong. "
            "Prefer: cd %s && uv run fda-rehydrate …",
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

    print_step(out, 1, _STEPS_TOTAL, "[cyan]>[/]", f"Load local corpus → [cyan]{corpus_dir}[/]")

    existing_docs, existing_ids = _load_corpus_state(corpus_dir)
    logging.info(
        "Corpus %s: %s letter(s) on disk.",
        corpus_dir,
        len(existing_docs),
    )

    print_step(
        out,
        2,
        _STEPS_TOTAL,
        "[cyan]>[/]",
        "Scan FDA listing (DataTables) · fetch HTML only for new slugs · stderr = progress",
    )

    result = run_ingest_new_letters(ingest_settings, existing_ids)
    logging.info(
        "Listing GETs (shell + DataTables): %s; rows seen: %s; new documents: %s",
        result.listing_pages_fetched,
        result.listing_rows_seen,
        len(result.documents),
    )
    logging.info(
        "FDA catalog: recordsFiltered=%s recordsTotal=%s raw_rows_traversed=%s",
        result.catalog_records_filtered,
        result.catalog_records_total,
        result.listing_raw_rows_traversed,
    )
    if result.fetch_errors:
        logging.warning(
            "%s letter fetch error(s), e.g. %s", len(result.fetch_errors), result.fetch_errors[0]
        )

    print_ingest_completion_report(
        out,
        result,
        run_label="Rehydrate · discovery",
        local_letters_before=len(existing_docs),
        local_letters_after=len(existing_docs) + len(result.documents),
    )

    if not result.documents:
        out.print(
            Panel.fit(
                "[green]ok Done.[/] No new letters — corpus and index unchanged.\n"
                "[dim]Compare FDA recordsFiltered vs local count in the table above.[/]",
                border_style="green",
            )
        )
        logging.info("No new letters; leaving corpus and index unchanged.")
        return

    print_step(
        out, 3, _STEPS_TOTAL, "[cyan]>[/]", "Merge new letters → write letters.jsonl + manifest"
    )

    merged: list[RawLetterDocument] = existing_docs + list(result.documents)
    write_corpus_jsonl(merged, corpus_dir, source="fda-rehydrate")
    logging.info("Wrote corpus with %s letter(s).", len(merged))

    print_step(out, 4, _STEPS_TOTAL, "[cyan]>[/]", "Chunk merged corpus")

    chunks = raw_letters_to_chunks(merged)
    logging.info("Built %s chunk(s).", len(chunks))

    print_step(
        out,
        5,
        _STEPS_TOTAL,
        "[cyan]>[/]",
        f"Rebuild hybrid index (embeddings) → [cyan]{artifact_root}[/]",
    )

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

    out.print()
    out.print(
        Panel.fit(
            f"[bold green]Rehydrate complete[/]\n"
            f"[white]Letters:[/] {len(merged)}  ·  "
            f"[white]Chunks:[/] {manifest.chunk_count}  ·  "
            f"[white]Model:[/] {manifest.embedding_model_id}",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
