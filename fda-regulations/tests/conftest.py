"""Shared pytest fixtures."""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fda_regulations.app.main import create_app
from fda_regulations.chunking.models import ChunkRecord
from fda_regulations.config import Settings
from fda_regulations.index.build import build_hybrid_index


@pytest.fixture
def artifact_dir(tmp_path: Path) -> Path:
    root = tmp_path / "artifacts"
    root.mkdir()
    chunks = (
        ChunkRecord(
            chunk_id="a:0",
            letter_id="a",
            letter_url="https://www.fda.gov/warning-letters/a",
            paragraph_index=0,
            text=(
                "Sterility assurance failures and aseptic processing concerns "
                "under 21 CFR Part 211."
            ),
            cfr_citations=("21 CFR Part 211",),
        ),
        ChunkRecord(
            chunk_id="b:0",
            letter_id="b",
            letter_url="https://www.fda.gov/warning-letters/b",
            paragraph_index=0,
            text="CAPA and complaint handling for medical devices under Part 820.",
            cfr_citations=(),
        ),
    )
    build_hybrid_index(
        root,
        chunks,
        embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
    )
    return root


@pytest.fixture
def client_relaxed() -> Generator[TestClient]:
    app = create_app(Settings(require_artifacts=False))
    with TestClient(app) as client:
        yield client


@pytest.fixture
def client_with_index(artifact_dir: Path) -> Generator[TestClient]:
    app = create_app(
        Settings(
            artifact_root=artifact_dir,
            require_artifacts=True,
        )
    )
    with TestClient(app) as client:
        yield client
