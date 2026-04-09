"""Shared value types used across HTTP, retrieval, and (later) taxonomy."""

from typing import Literal

ClassificationMethod = Literal["cfr_rule", "keyword", "unclassified"]
