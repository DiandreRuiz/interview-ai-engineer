"""FastAPI application factory and ASGI entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from fda_regulations.app.routers import health, search
from fda_regulations.config import Settings
from fda_regulations.search.bootstrap import load_retriever


def _index_ready(settings: Settings) -> bool:
    """True when strict artifact validation ran successfully at startup."""
    if not settings.require_artifacts:
        return False
    manifest = settings.artifact_root.expanduser().resolve() / "index_manifest.json"
    return manifest.is_file()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app (use this in tests with overridden ``Settings``)."""
    resolved = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = resolved
        app.state.retriever = load_retriever(resolved)
        app.state.index_ready = _index_ready(resolved)
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
