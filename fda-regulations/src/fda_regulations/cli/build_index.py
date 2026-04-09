"""CLI: corpus → chunks → hybrid index artifacts + optional phase-1 report."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from fda_regulations.chunk_pipeline import raw_letters_to_chunks
from fda_regulations.config import Settings
from fda_regulations.index.build import build_hybrid_index
from fda_regulations.ingest.corpus import iter_corpus_letters
from fda_regulations.ingest.scrape import run_ingest
from fda_regulations.ingest.scrape.models import RawLetterDocument
from fda_regulations.reporting import write_phase1_ingest_report


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Build hybrid BM25 + dense index from corpus JSONL (or scrape first).",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=None,
        help="Directory for index_manifest.json and sidecars (default: ARTIFACT_ROOT).",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=None,
        help="Directory with letters.jsonl (default: resolved INGEST_CORPUS_DIR).",
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default=None,
        help="Override INDEX_EMBEDDING_MODEL (sentence-transformers id).",
    )
    parser.add_argument(
        "--scrape-first",
        action="store_true",
        help="Run live FDA scrape before indexing (respects ingest caps in env).",
    )
    parser.add_argument(
        "--write-corpus",
        action="store_true",
        help="With --scrape-first, also write corpus JSONL to corpus dir.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write a markdown phase-1 report to this path.",
    )
    args = parser.parse_args()

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

    documents: list[RawLetterDocument]
    if args.scrape_first:
        from fda_regulations.ingest.corpus import write_corpus_jsonl

        ingest_result = run_ingest(settings)
        documents = list(ingest_result.documents)
        logging.info("Scraped %s letter document(s).", len(documents))
        if args.write_corpus:
            write_corpus_jsonl(documents, corpus_dir)
            logging.info("Wrote corpus under %s", corpus_dir)
    else:
        documents = list(iter_corpus_letters(corpus_dir))
        logging.info("Loaded %s letter document(s) from corpus.", len(documents))

    if not documents:
        logging.error("No letters to index. Scrape with --scrape-first or build corpus first.")
        raise SystemExit(1)

    chunks = raw_letters_to_chunks(documents)
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
            letter_count=len(documents),
            chunk_count=len(chunks),
            chunks_with_cfr=with_cfr,
            embedding_model_id=model_id,
            artifact_root=artifact_root,
            corpus_dir=corpus_dir,
        )
        logging.info("Wrote report %s", args.report)


if __name__ == "__main__":
    main()
