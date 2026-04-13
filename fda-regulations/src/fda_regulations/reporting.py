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
    corpus_letter_count: int | None = None,
) -> None:
    """Write the phase-1 summary as ``fda-build-index --report``.

    ``corpus_letter_count`` is the total letters in the corpus JSONL (before
    chunking filters out letters with no extractable ``<p>`` content).  When
    provided, the difference from ``letter_count`` is reported as excluded.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    cfr_pct = 0.0 if chunk_count == 0 else 100.0 * chunks_with_cfr / chunk_count

    lines = [
        "# Phase 1 ingest / index report (auto-generated)",
        "",
        "## Summary statistics",
        "",
        f"- **Artifact root:** `{artifact_root}`",
        f"- **Corpus directory:** `{corpus_dir}`",
    ]
    if corpus_letter_count is not None:
        lines.append(f"- **Letters in corpus:** {corpus_letter_count}")
    lines += [
        f"- **Letters with extractable paragraphs (indexed):** {letter_count}",
        f"- **Chunks:** {chunk_count}",
        f"- **Chunks with ≥1 CFR citation (regex):** {chunks_with_cfr} ({cfr_pct:.1f}%)",
        f"- **Embedding model:** `{embedding_model_id}`",
    ]
    if corpus_letter_count is not None and corpus_letter_count > letter_count:
        excluded = corpus_letter_count - letter_count
        lines.append(
            f"- **Letters excluded (no paragraph content):** {excluded}",
        )

    lines += [
        "",
        "## Inclusion criteria",
        "",
        "- Published on the FDA Warning Letters listing page (DataTables AJAX discovery)",
        "- Detail page returns HTTP 200 with a recognized warning-letter URL pattern",
        "- HTML contains `article#main-content` or `#main-content` region",
        "- At least one non-empty `<p>` element in the main content region",
        "",
        "## Exclusion criteria",
        "",
        "- Non-200 HTTP responses (connection errors, redirects to non-letter pages)",
        "- Listing rows linking to index/about pages rather than individual letters",
        "- Letters with no extractable paragraph content (main region present but all "
        "`<p>` elements empty)",
        "- Duplicate `letter_id` slugs within a scrape run (deduplicated by URL slug)",
        "- Empty or malformed DataTables listing rows that fail to parse",
        "",
        "---",
        "",
        "For the full reasoning and retrieval next steps, "
        "see `reports/phase1.md` (hand-written) and "
        "`context/plans/implementation-plan.md`.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
