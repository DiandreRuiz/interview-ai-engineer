"""Hybrid search endpoint (thin handler → retriever protocol)."""

import asyncio
from typing import cast

from fastapi import APIRouter, HTTPException, Request

from fda_regulations.app.models import SearchHit, SearchRequest, SearchResponse
from fda_regulations.search.protocol import RetrievalHit, Retriever
from fda_regulations.search.query import prepare_search_query

router = APIRouter(tags=["search"])


def _to_search_hit(hit: RetrievalHit) -> SearchHit:
    return SearchHit(
        chunk_id=hit.chunk_id,
        score=hit.score,
        snippet=hit.snippet,
        letter_id=hit.letter_id,
        letter_url=hit.letter_url,
        paragraph_index=hit.paragraph_index,
    )


@router.post("/search", response_model=SearchResponse)
async def search(request: Request, body: SearchRequest) -> SearchResponse:
    r = cast(Retriever, request.app.state.retriever)
    try:
        prepared = prepare_search_query(body.query)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=[{"loc": ["body", "query"], "msg": str(exc), "type": "value_error"}],
        ) from exc

    raw_hits = await asyncio.to_thread(
        r.search,
        prepared,
        top_k=body.top_k,
    )

    return SearchResponse(hits=[_to_search_hit(h) for h in raw_hits])
