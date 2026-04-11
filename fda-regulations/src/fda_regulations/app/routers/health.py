"""Liveness and index readiness."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from fda_regulations.app.models import HealthResponse

router = APIRouter(tags=["health"])


def get_index_ready(request: Request) -> bool:
    """Whether strict artifact validation ran at startup (see ``create_app`` lifespan)."""
    return bool(request.app.state.index_ready)


IndexReadyDep = Annotated[bool, Depends(get_index_ready)]


@router.get("/health", response_model=HealthResponse)
def health(index_ready: IndexReadyDep) -> HealthResponse:
    return HealthResponse(index_ready=index_ready)
