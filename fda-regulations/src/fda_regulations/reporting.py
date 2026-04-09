"""Shared markdown reports (phase-1 ingest stats, etc.)."""

from __future__ import annotations

from pathlib import Path


def write_phase1_ingest_report(
    path: Path,
    *,
    letter_count: int,
    chunk_count: int,
    chunks_with_cfr: int,
    embedding_model_id: str,
    artifact_root: Path,
    corpus_dir: Path,
) -> None:
    """Write the same phase-1 summary as ``fda-build-index --report``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cfr_pct = 0.0 if chunk_count == 0 else 100.0 * chunks_with_cfr / chunk_count
    lines = [
        "# Phase 1 ingest / index report",
        "",
        f"- **Artifact root:** `{artifact_root}`",
        f"- **Corpus directory:** `{corpus_dir}`",
        f"- **Letters indexed:** {letter_count}",
        f"- **Chunks:** {chunk_count}",
        f"- **Chunks with ≥1 CFR citation (regex):** {chunks_with_cfr} ({cfr_pct:.1f}%)",
        f"- **Embedding model:** `{embedding_model_id}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
