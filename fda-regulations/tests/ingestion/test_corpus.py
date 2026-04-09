"""Corpus JSONL write/read and error paths."""

import json
from pathlib import Path

import pytest

from fda_regulations.ingest.corpus import (
    CORPUS_LETTERS_JSONL,
    CORPUS_MANIFEST_NAME,
    corpus_letter_count,
    iter_corpus_letters,
    read_corpus_manifest,
    write_corpus_jsonl,
)
from fda_regulations.ingest.scrape.models import RawLetterDocument, utc_now


def test_write_then_iter_roundtrip(tmp_path: Path) -> None:
    doc = RawLetterDocument(
        letter_id="acme-123",
        url="https://www.fda.gov/inspections/.../warning-letters/acme-123",
        html="<html><body>Hi</body></html>",
        fetched_at_utc=utc_now(),
        company_name="Acme",
        posted_date="03/01/2025",
        letter_issue_date="02/15/2025",
    )
    stats = write_corpus_jsonl((doc,), tmp_path)
    assert stats.documents_written == 1
    assert stats.letters_jsonl.is_file()
    assert stats.manifest_path.is_file()

    loaded = tuple(iter_corpus_letters(tmp_path))
    assert len(loaded) == 1
    assert loaded[0].letter_id == "acme-123"
    assert loaded[0].html == doc.html
    assert loaded[0].company_name == "Acme"


def test_read_corpus_manifest_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Missing corpus manifest"):
        read_corpus_manifest(tmp_path)


def test_iter_corpus_letters_missing_jsonl_raises(tmp_path: Path) -> None:
    manifest = {
        "schema_version": 1,
        "built_at_utc": "2026-01-01T00:00:00Z",
        "letter_count": 0,
        "source": "fda-scrape",
    }
    (tmp_path / CORPUS_MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    with pytest.raises(FileNotFoundError, match="Missing corpus JSONL"):
        next(iter_corpus_letters(tmp_path))


def test_iter_corpus_letters_invalid_jsonl_raises(tmp_path: Path) -> None:
    doc = RawLetterDocument(
        letter_id="ok",
        url="https://example.test/warning-letters/ok",
        html="<p>x</p>",
        fetched_at_utc=utc_now(),
    )
    write_corpus_jsonl((doc,), tmp_path)
    jsonl = tmp_path / CORPUS_LETTERS_JSONL
    jsonl.write_text(jsonl.read_text(encoding="utf-8") + "not valid json\n", encoding="utf-8")
    gen = iter_corpus_letters(tmp_path)
    assert next(gen).letter_id == "ok"
    with pytest.raises(ValueError, match="Invalid JSONL record"):
        next(gen)


def test_corpus_letter_count_matches_manifest(tmp_path: Path) -> None:
    docs = (
        RawLetterDocument(
            letter_id="a",
            url="https://example.test/a",
            html="<p>a</p>",
            fetched_at_utc=utc_now(),
        ),
        RawLetterDocument(
            letter_id="b",
            url="https://example.test/b",
            html="<p>b</p>",
            fetched_at_utc=utc_now(),
        ),
    )
    write_corpus_jsonl(docs, tmp_path)
    assert corpus_letter_count(tmp_path) == 2
