"""Reciprocal rank fusion over ranked chunk id lists."""

from __future__ import annotations


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    *,
    k: float,
) -> dict[str, float]:
    """Sum ``1 / (k + rank)`` for each chunk id across lists (1-based ranks)."""
    scores: dict[str, float] = {}
    for ids in ranked_lists:
        for rank, chunk_id in enumerate(ids, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return scores
