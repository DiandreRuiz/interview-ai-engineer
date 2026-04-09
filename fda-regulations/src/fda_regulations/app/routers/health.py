"""Liveness and index readiness."""

from fastapi import APIRouter, Request

from fda_regulations.app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    index_ready = bool(getattr(request.app.state, "index_ready", False))
    return HealthResponse(index_ready=index_ready)
