"""Persist and load scraped warning-letter HTML for offline chunking and indexing."""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from fda_regulations.ingest.scrape.models import RawLetterDocument

CORPUS_LETTERS_JSONL = "letters.jsonl"
CORPUS_MANIFEST_NAME = "corpus_manifest.json"
_CORPUS_SCHEMA_VERSION = 1


class CorpusManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=_CORPUS_SCHEMA_VERSION)
    built_at_utc: datetime
    letter_count: int
    source: str = Field(default="fda-scrape", description="Provenance label for the batch.")


class CorpusBuildStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    corpus_dir: Path
    letters_jsonl: Path
    manifest_path: Path
    documents_written: int


def default_corpus_dir(artifact_root: Path) -> Path:
    """Default ``{artifact_root}/corpus`` (see implementation plan)."""
    return artifact_root.expanduser().resolve() / "corpus"


def write_corpus_jsonl(
    documents: Sequence[RawLetterDocument],
    corpus_dir: Path,
    *,
    source: str = "fda-scrape",
) -> CorpusBuildStats:
    """Write one JSON line per letter plus ``corpus_manifest.json``."""
    root = corpus_dir.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    jsonl_path = root / CORPUS_LETTERS_JSONL
    manifest_path = root / CORPUS_MANIFEST_NAME

    with jsonl_path.open("w", encoding="utf-8") as f:
        for doc in documents:
            line = doc.model_dump_json()
            f.write(line)
            f.write("\n")

    manifest = CorpusManifest(
        built_at_utc=datetime.now(UTC),
        letter_count=len(documents),
        source=source,
    )
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return CorpusBuildStats(
        corpus_dir=root,
        letters_jsonl=jsonl_path,
        manifest_path=manifest_path,
        documents_written=len(documents),
    )


def read_corpus_manifest(corpus_dir: Path) -> CorpusManifest:
    path = corpus_dir.expanduser().resolve() / CORPUS_MANIFEST_NAME
    if not path.is_file():
        msg = f"Missing corpus manifest: {path}"
        raise FileNotFoundError(msg)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return CorpusManifest.model_validate(raw)


def iter_corpus_letters(corpus_dir: Path) -> Iterator[RawLetterDocument]:
    """Stream letters from ``letters.jsonl`` (raises if manifest missing)."""
    root = corpus_dir.expanduser().resolve()
    read_corpus_manifest(root)  # validate corpus dir is complete
    jsonl_path = root / CORPUS_LETTERS_JSONL
    if not jsonl_path.is_file():
        msg = f"Missing corpus JSONL: {jsonl_path}"
        raise FileNotFoundError(msg)

    with jsonl_path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield RawLetterDocument.model_validate_json(line)
            except ValueError as exc:
                msg = f"Invalid JSONL record at {jsonl_path}:{line_no}: {exc}"
                raise ValueError(msg) from exc


def corpus_letter_count(corpus_dir: Path) -> int:
    """Return manifest letter_count without reading the full JSONL."""
    return read_corpus_manifest(corpus_dir).letter_count
