"""Application settings (environment + defaults)."""

from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from fda_regulations.site_urls import FDA_WARNING_LETTERS_LISTING_URL


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
    index_embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence-transformers model id used when building the dense index.",
    )

    fda_user_agent: str = Field(
        default="fda-regulations-poc/0.1 (research; contact: local dev)",
        description="User-Agent for FDA HTTP requests (ingest).",
    )
    ingest_listing_base_url: str = Field(
        default=FDA_WARNING_LETTERS_LISTING_URL,
        description=(
            "FDA warning letters hub URL (shell page); letter discovery uses DataTables AJAX "
            "on the same host."
        ),
    )
    ingest_listing_batch_size: int = Field(
        default=100,
        ge=1,
        le=500,
        description="DataTables ``length`` parameter (rows per AJAX listing request).",
    )
    ingest_max_listing_pages: int | None = Field(
        default=None,
        description=(
            "Cap DataTables AJAX batches after the shell GET; None = page until the catalog ends."
        ),
    )
    ingest_max_letters: int | None = Field(
        default=None,
        description="Cap letters fetched after discovery; None = no cap.",
    )
    ingest_request_delay_seconds: float = Field(
        default=0.5,
        ge=0.0,
        description="Sleep between HTTP calls to avoid hammering FDA servers.",
    )
    ingest_corpus_dir: Path | None = Field(
        default=None,
        description="Raw scrape JSONL root; default is ARTIFACT_ROOT/corpus.",
    )

    @computed_field
    @property
    def resolved_ingest_corpus_dir(self) -> Path:
        root = self.artifact_root.expanduser().resolve()
        if self.ingest_corpus_dir is not None:
            return self.ingest_corpus_dir.expanduser().resolve()
        return root / "corpus"
