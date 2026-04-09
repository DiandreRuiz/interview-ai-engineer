"""Paragraph-level chunks and CFR extraction for warning letters."""

from fda_regulations.chunking.chunk_letter import chunk_raw_letter
from fda_regulations.chunking.models import ChunkRecord

__all__ = ["ChunkRecord", "chunk_raw_letter"]
