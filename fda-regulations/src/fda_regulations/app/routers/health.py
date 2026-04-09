"""Liveness and index readiness."""

from fastapi import APIRouter, Request

from fda_regulations.app.models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    return HealthResponse(index_ready=bool(request.app.state.index_ready))
