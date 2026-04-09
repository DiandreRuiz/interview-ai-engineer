"""HTTP client factory for FDA ingest."""

import httpx

from fda_regulations.config import Settings


def build_ingest_client(settings: Settings) -> httpx.Client:
    timeout = httpx.Timeout(60.0, connect=15.0)
    headers = {"User-Agent": settings.fda_user_agent}
    return httpx.Client(timeout=timeout, headers=headers, follow_redirects=True)
