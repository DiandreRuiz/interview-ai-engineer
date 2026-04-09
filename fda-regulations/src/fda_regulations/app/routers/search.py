"""Hybrid search endpoint (thin handler → retriever protocol)."""

import asyncio
from typing import cast

from fastapi import APIRouter, HTTPException, Request

from fda_regulations.app.schemas import SearchHit, SearchRequest, SearchResponse
from fda_regulations.search.protocol import RetrievalHit, Retriever

router = APIRouter(tags=["search"])


def _to_search_hit(hit: RetrievalHit) -> SearchHit:
    return SearchHit(
        chunk_id=hit.chunk_id,
        score=hit.score,
        snippet=hit.snippet,
        letter_id=hit.letter_id,
        letter_url=hit.letter_url,
        paragraph_index=hit.paragraph_index,
        taxonomy_label=hit.taxonomy_label,
        classification_method=hit.classification_method,
    )


@router.post("/search", response_model=SearchResponse)
async def search(request: Request, body: SearchRequest) -> SearchResponse:
    retriever = getattr(request.app.state, "retriever", None)
    if retriever is None:
        raise HTTPException(status_code=503, detail="Search backend not initialized")

    r = cast(Retriever, retriever)
    try:
        raw_hits = await asyncio.to_thread(
            r.search,
            body.query,
            top_k=body.top_k,
            label_filter=body.label_filter,
            label_boost=body.label_boost,
        )
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail="Search backend not fully implemented") from exc

    return SearchResponse(hits=[_to_search_hit(h) for h in raw_hits])
