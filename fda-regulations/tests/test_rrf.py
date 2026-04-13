"""Reciprocal rank fusion (pure)."""

from fda_regulations.index.rrf import reciprocal_rank_fusion


def test_rrf_combines_two_lists() -> None:
    fused = reciprocal_rank_fusion(
        [["a", "b"], ["b", "c"]],
        k=60.0,
    )
    assert fused["b"] > fused["a"]
    assert fused["b"] > fused["c"]
