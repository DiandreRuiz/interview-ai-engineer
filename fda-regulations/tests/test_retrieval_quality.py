"""Retrieval quality: 20 queries grounded in fixture warning-letter corpus prose.

The corpus under ``tests/fixtures/retrieval_eval_corpus/`` mirrors FDA warning-letter
topics (CGMP, devices, data integrity, dietary supplements, etc.). Each case asserts
that the hybrid retriever (BM25 + dense + RRF) returns the gold paragraph chunk in
the top ``k`` results — a lightweight recall@k check suitable for CI.

Gold labels are ``(letter_id, paragraph_index)`` matching production chunk ids
(``letter_id:index``).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from fda_regulations.chunking import raw_letters_to_chunks
from fda_regulations.config import Settings
from fda_regulations.index.build import build_hybrid_index
from fda_regulations.index.load import load_hybrid_retriever
from fda_regulations.index.retriever import HybridRetriever
from fda_regulations.ingest.corpus import iter_corpus_letters
from fda_regulations.search.query import prepare_search_query

_FIXTURE_CORPUS = Path(__file__).resolve().parent / "fixtures" / "retrieval_eval_corpus"
_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_RECALL_AT_K = 10

# Natural queries (not full paragraph copy) aligned to a specific paragraph in the fixture.
# Format: (query, letter_id, paragraph_index)
_RETRIEVAL_QUALITY_CASES: tuple[tuple[str, str, int], ...] = (
    (
        "Grade A smoke studies aseptic processing environmental monitoring sterile areas",
        "eval-sterility-2024",
        1,
    ),
    (
        "media fill worst-case operational validation positive units root cause investigation",
        "eval-sterility-2024",
        2,
    ),
    (
        "design controls 21 CFR 820.30 design inputs verification infusion pump software",
        "eval-device-820-2024",
        1,
    ),
    (
        "complaint records trending serious injuries corrective actions validated implementation",
        "eval-device-820-2024",
        2,
    ),
    (
        "chromatography integration parameters changed after injection stability electronic raw data",
        "eval-data-integrity-2024",
        1,
    ),
    (
        "LIMS administrator passwords unidentified users modify sample results ALCOA laboratory",
        "eval-data-integrity-2024",
        2,
    ),
    (
        "master manufacturing records in-process controls immune health botanical capsules Part 111",
        "eval-dietary-2024",
        1,
    ),
    (
        "identity tests botanical powders overseas suppliers incoming specifications",
        "eval-dietary-2024",
        2,
    ),
    (
        "water formulation microbial contamination sanitization holding tanks cosmetic",
        "eval-cosmetics-2024",
        1,
    ),
    (
        "batch records lot CG-88 fragrance components quantity blended finished product",
        "eval-cosmetics-2024",
        2,
    ),
    (
        "donor screening vital signs deferral documentation plasma collections records",
        "eval-blood-2024",
        1,
    ),
    (
        "plasma storage equipment calibration schedule temperature excursion logs",
        "eval-blood-2024",
        2,
    ),
    (
        "ISO 5 hood mold environmental monitoring investigations outsourcing facility 503B",
        "eval-compounding-2024",
        1,
    ),
    (
        "beyond-use dating high-risk sterile preparations stability container closure system",
        "eval-compounding-2024",
        2,
    ),
    (
        "periodic safety update reports late product X-100 serious events narrative ICSRs",
        "eval-mah-2024",
        1,
    ),
    (
        "signal detection meeting minutes medical review disproportionality adverse reactions",
        "eval-mah-2024",
        2,
    ),
    (
        "flavored tobacco retail age verification point of sale covered products",
        "eval-tobacco-2024",
        1,
    ),
    (
        "modified risk claims promotional materials receipts inventory records",
        "eval-tobacco-2024",
        2,
    ),
    (
        "shipment IMP-2024-09 unapproved new drugs diabetes directions for use import",
        "eval-import-2024",
        1,
    ),
    (
        "register foreign drug establishment list products FDA 21 CFR Part 207",
        "eval-import-2024",
        2,
    ),
)


def _fixture_letters() -> Iterator:
    if not _FIXTURE_CORPUS.is_dir():
        pytest.skip(f"Missing retrieval eval corpus: {_FIXTURE_CORPUS}")
    yield from iter_corpus_letters(_FIXTURE_CORPUS)


@pytest.fixture(scope="module")
def retrieval_eval_retriever(tmp_path_factory: pytest.TempPathFactory) -> HybridRetriever:
    chunks = raw_letters_to_chunks(_fixture_letters())
    assert len(chunks) >= 20
    root = tmp_path_factory.mktemp("retrieval_eval_index")
    build_hybrid_index(
        root,
        chunks,
        embedding_model_id=_EMBEDDING_MODEL,
    )
    settings = Settings(
        artifact_root=root,
        require_artifacts=True,
        rrf_k=60,
        search_top_k_sparse=50,
        search_top_k_dense=50,
        index_embedding_model=_EMBEDDING_MODEL,
    )
    return load_hybrid_retriever(root, settings)


@pytest.mark.parametrize(
    ("query", "letter_id", "paragraph_index"),
    _RETRIEVAL_QUALITY_CASES,
    ids=[f"q{i:02d}" for i in range(1, len(_RETRIEVAL_QUALITY_CASES) + 1)],
)
def test_retrieval_recall_at_k(
    retrieval_eval_retriever: HybridRetriever,
    query: str,
    letter_id: str,
    paragraph_index: int,
) -> None:
    gold = f"{letter_id}:{paragraph_index}"
    prepared = prepare_search_query(query)
    hits = retrieval_eval_retriever.search(prepared, top_k=_RECALL_AT_K)
    found = [h.chunk_id for h in hits]
    assert gold in found, (
        f"Expected {gold!r} in top-{_RECALL_AT_K} for query {query!r}; got {found!r}"
    )


def test_retrieval_quality_case_count_is_twenty() -> None:
    assert len(_RETRIEVAL_QUALITY_CASES) == 20
