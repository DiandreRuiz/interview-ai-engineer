"""Hybrid search endpoint (thin handler → retriever protocol)."""

import asyncio
import logging
import time
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request

from fda_regulations.app.models import SearchHit, SearchRequest, SearchResponse
from fda_regulations.search.protocol import RetrievalHit, Retriever
from fda_regulations.search.query import prepare_search_query

router = APIRouter(tags=["search"])
log = logging.getLogger(__name__)


def get_retriever(request: Request) -> Retriever:
    """Retriever bound at app startup (``create_app`` lifespan); cast bridges untyped app.state."""
    return cast(Retriever, request.app.state.retriever)


RetrieverDep = Annotated[Retriever, Depends(get_retriever)]


def _to_search_hit(hit: RetrievalHit) -> SearchHit:
    return SearchHit(
        chunk_id=hit.chunk_id,
        score=hit.score,
        snippet=hit.snippet,
        letter_id=hit.letter_id,
        letter_url=hit.letter_url,
        paragraph_index=hit.paragraph_index,
        cfr_citations=hit.cfr_citations,
    )


@router.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest, retriever: RetrieverDep) -> SearchResponse:
    try:
        prepared = prepare_search_query(body.query)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=[{"loc": ["body", "query"], "msg": str(exc), "type": "value_error"}],
        ) from exc

    t0 = time.perf_counter()
    raw_hits = await asyncio.to_thread(
        retriever.search,
        prepared,
        top_k=body.top_k,
    )
    latency_ms = (time.perf_counter() - t0) * 1000

    hits = [_to_search_hit(h) for h in raw_hits]
    log.info(
        "query=%r top_k=%d results=%d latency_ms=%.1f top_chunks=%s",
        body.query[:120],
        body.top_k,
        len(hits),
        latency_ms,
        [h.chunk_id for h in hits[:5]],
    )
    return SearchResponse(hits=hits)
