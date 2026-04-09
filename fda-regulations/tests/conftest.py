"""Shared pytest fixtures."""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fda_regulations.app.main import create_app
from fda_regulations.config import Settings


@pytest.fixture
def artifact_dir(tmp_path: Path) -> Path:
    root = tmp_path / "artifacts"
    root.mkdir()
    (root / "index_manifest.json").write_text('{"schema_version": 1}', encoding="utf-8")
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
