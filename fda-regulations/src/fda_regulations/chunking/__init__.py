"""Paragraph-level chunks and CFR extraction for warning letters."""

from __future__ import annotations

from collections.abc import Iterable

from fda_regulations.chunking.chunk_letter import chunk_raw_letter
from fda_regulations.chunking.models import ChunkRecord
from fda_regulations.ingest.scrape.models import RawLetterDocument

__all__ = ["ChunkRecord", "chunk_raw_letter", "raw_letters_to_chunks"]


def raw_letters_to_chunks(documents: Iterable[RawLetterDocument]) -> list[ChunkRecord]:
    """Chunk each letter into paragraph-level records."""
    out: list[ChunkRecord] = []
    for doc in documents:
        out.extend(chunk_raw_letter(doc))
    return out
