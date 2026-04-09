"""Lifespan / startup failure modes."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fda_regulations.app.main import create_app
from fda_regulations.config import Settings


def test_startup_fails_when_manifest_missing(tmp_path: Path) -> None:
    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    settings = Settings(artifact_root=empty_root, require_artifacts=True)
    with pytest.raises(FileNotFoundError), TestClient(create_app(settings)):
        pass
