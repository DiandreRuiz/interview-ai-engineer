"""Application settings (environment + defaults)."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    artifact_root: Path = Field(
        default=Path("artifacts"),
        description="Directory containing index_manifest.json and index artifacts.",
    )
    require_artifacts: bool = Field(
        default=True,
        description="If true, startup fails when the index manifest is missing.",
    )
    rrf_k: int = Field(
        default=60,
        ge=1,
        description="RRF rank constant k (implementation-plan appendix).",
    )
    search_top_k_sparse: int = Field(
        default=50,
        ge=1,
        description="BM25 candidate count before fusion.",
    )
    search_top_k_dense: int = Field(
        default=50,
        ge=1,
        description="Dense candidate count before fusion.",
    )
