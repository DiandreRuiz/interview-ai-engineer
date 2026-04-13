"""Optional retrieval checks against a **pre-built** hybrid index on disk.

Set ``FDA_EVAL_ARTIFACT_ROOT`` to a directory containing ``index_manifest.json``,
``chunks.jsonl``, ``embeddings.npy``, and ``chunk_order.json`` (same layout as
``fda-build-index``). The test picks 20 substantive chunks deterministically from
``chunks.jsonl``, builds a short query from each chunk's own prose (oracle / self
retrieval), and asserts **recall@10** for the hybrid retriever.

This exercises retrieval on **your current indexed corpus** without checking in
large artifacts. Skip in CI when the env var is unset.

Example::

    FDA_EVAL_ARTIFACT_ROOT=artifacts uv run pytest tests/test_retrieval_quality_artifacts.py -v
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from fda_regulations.chunking.models import ChunkRecord
from fda_regulations.config import Settings
from fda_regulations.index.load import load_hybrid_retriever
from fda_regulations.index.retriever import HybridRetriever
from fda_regulations.search.query import prepare_search_query

_ARTIFACT_ROOT_ENV = "FDA_EVAL_ARTIFACT_ROOT"
_MIN_CHUNK_CHARS = 120
_ORACLE_WORDS = 14
_RECALL_AT_K = 10
_NUM_CASES = 20


def _artifact_root() -> Path | None:
    raw = os.environ.get(_ARTIFACT_ROOT_ENV, "").strip()
    if not raw:
        return None
    p = Path(raw).expanduser().resolve()
    if not (p / "index_manifest.json").is_file():
        pytest.skip(f"{_ARTIFACT_ROOT_ENV}={raw!r} missing index_manifest.json")
    if not (p / "chunks.jsonl").is_file():
        pytest.skip(f"{_ARTIFACT_ROOT_ENV}={raw!r} missing chunks.jsonl")
    return p


def _read_all_chunks(path: Path) -> tuple[ChunkRecord, ...]:
    out: list[ChunkRecord] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(ChunkRecord.model_validate_json(line))
    return tuple(out)


def _oracle_query(text: str) -> str:
    words = text.split()
    if len(words) <= _ORACLE_WORDS + 4:
        return " ".join(words)
    start = max(0, len(words) // 2 - _ORACLE_WORDS // 2)
    return " ".join(words[start : start + _ORACLE_WORDS])


def _select_eval_chunks(chunks: tuple[ChunkRecord, ...]) -> tuple[ChunkRecord, ...]:
    eligible = [c for c in chunks if len(c.text) >= _MIN_CHUNK_CHARS]
    if len(eligible) < _NUM_CASES:
        pytest.skip(
            f"Need at least {_NUM_CASES} chunks with text length >= {_MIN_CHUNK_CHARS}; "
            f"found {len(eligible)}"
        )
    eligible.sort(key=lambda c: c.chunk_id)
    stride = max(1, len(eligible) // _NUM_CASES)
    picked = [eligible[i * stride] for i in range(_NUM_CASES)]
    return tuple(picked)


@pytest.fixture(scope="module")
def artifact_eval_retriever() -> HybridRetriever:
    root = _artifact_root()
    if root is None:
        pytest.skip(
            f"Set {_ARTIFACT_ROOT_ENV} to a built index directory to run artifact retrieval eval"
        )
    settings = Settings(
        artifact_root=root,
        require_artifacts=True,
    )
    return load_hybrid_retriever(root, settings)


@pytest.fixture(scope="module")
def artifact_oracle_cases() -> tuple[tuple[str, str], ...]:
    root = _artifact_root()
    if root is None:
        pytest.skip(f"Set {_ARTIFACT_ROOT_ENV} to run artifact retrieval eval")
    chunks = _read_all_chunks(root / "chunks.jsonl")
    selected = _select_eval_chunks(chunks)
    return tuple((_oracle_query(c.text), c.chunk_id) for c in selected)


@pytest.mark.parametrize("case_index", range(_NUM_CASES))
def test_artifact_oracle_recall_at_k(
    artifact_eval_retriever: HybridRetriever,
    artifact_oracle_cases: tuple[tuple[str, str], ...],
    case_index: int,
) -> None:
    query, gold_chunk_id = artifact_oracle_cases[case_index]
    prepared = prepare_search_query(query)
    hits = artifact_eval_retriever.search(prepared, top_k=_RECALL_AT_K)
    found = [h.chunk_id for h in hits]
    assert gold_chunk_id in found, (
        f"Expected {gold_chunk_id!r} in top-{_RECALL_AT_K} for oracle query; got {found!r}"
    )
