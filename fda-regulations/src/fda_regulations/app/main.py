"""FastAPI application factory and ASGI entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from fda_regulations.app.routers import health, search
from fda_regulations.config import Settings
from fda_regulations.search.bootstrap import load_retriever


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app (use this in tests with overridden ``Settings``)."""
    resolved = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = resolved
        app.state.retriever = load_retriever(resolved)
        # Strict mode already validated the manifest inside ``load_retriever``.
        app.state.index_ready = bool(resolved.require_artifacts)
        yield

    app = FastAPI(
        title="FDA regulations hybrid search",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(search.router)
    return app


app = create_app()
