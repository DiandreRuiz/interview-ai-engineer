"""Search endpoint contract (no live FDA network)."""

from fastapi.testclient import TestClient


def test_search_returns_hits_array(client_relaxed: TestClient) -> None:
    response = client_relaxed.post("/search", json={"query": "sterility assurance", "top_k": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["hits"] == []


def test_search_validation_empty_query(client_relaxed: TestClient) -> None:
    response = client_relaxed.post("/search", json={"query": "", "top_k": 5})
    assert response.status_code == 422


def test_search_validation_whitespace_only_query(client_relaxed: TestClient) -> None:
    response = client_relaxed.post("/search", json={"query": "   \t  ", "top_k": 5})
    assert response.status_code == 422


def test_search_no_searchable_tokens(client_relaxed: TestClient) -> None:
    response = client_relaxed.post("/search", json={"query": "…", "top_k": 5})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "query"]


def test_search_with_index_returns_hybrid_hits(client_with_index: TestClient) -> None:
    response = client_with_index.post(
        "/search",
        json={"query": "aseptic processing concerns 21 cfr part 211", "top_k": 3},
    )
    assert response.status_code == 200
    hits = response.json()["hits"]
    assert len(hits) >= 1
    chunk_ids = [h["chunk_id"] for h in hits]
    assert "a:0" in chunk_ids
    assert hits[0]["snippet"]

    hit_a = next(h for h in hits if h["chunk_id"] == "a:0")
    assert "21 CFR Part 211" in hit_a["cfr_citations"]
