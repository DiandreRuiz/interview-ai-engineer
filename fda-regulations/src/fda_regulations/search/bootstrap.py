"""Construct a retriever from settings and on-disk artifact layout."""

import json
from pathlib import Path

from fda_regulations.config import Settings
from fda_regulations.index.load import is_hybrid_index_manifest, load_hybrid_retriever
from fda_regulations.search.protocol import Retriever
from fda_regulations.search.stub import StubRetriever

_MANIFEST_NAME = "index_manifest.json"
_EXPECTED_SCHEMA_VERSION = 1


def _read_manifest(manifest_path: Path) -> dict[str, object]:
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = f"{manifest_path} must contain a JSON object"
        raise ValueError(msg)
    return raw


def load_retriever(settings: Settings) -> Retriever:
    """Load retriever; validates artifact layout when ``require_artifacts`` is true."""
    if not settings.require_artifacts:
        return StubRetriever()

    root = settings.artifact_root.expanduser().resolve()
    if not root.is_dir():
        msg = f"ARTIFACT_ROOT is not a directory: {root}"
        raise FileNotFoundError(msg)

    manifest_path = root / _MANIFEST_NAME
    if not manifest_path.is_file():
        msg = f"Missing index manifest: {manifest_path}"
        raise FileNotFoundError(msg)

    data = _read_manifest(manifest_path)
    schema_version = data.get("schema_version")
    if schema_version != _EXPECTED_SCHEMA_VERSION:
        msg = (
            f"Unsupported index schema in {manifest_path}: "
            f"expected schema_version {_EXPECTED_SCHEMA_VERSION}, got {schema_version!r}"
        )
        raise ValueError(msg)

    if is_hybrid_index_manifest(data):
        return load_hybrid_retriever(root, settings)

    msg = (
        f"Index manifest at {manifest_path} is missing hybrid fields "
        f"(index_backend, embedding_model_id). Run: uv run fda-build-index …"
    )
    raise ValueError(msg)
