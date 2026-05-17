"""
LexGuard — Centralized configuration via pydantic-settings.
All values are read from environment variables (or .env file).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LlamaParse ────────────────────────────────────────────────────────
    llamaparse_api_key: str

    # ── HuggingFace Inference API (Embeddings) ────────────────────────────
    hf_api_key: str
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    embedding_dimensions: int = 768

    # ── Qdrant Cloud ──────────────────────────────────────────────────────
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str = "lexguard_contracts"

    # ── NVIDIA NIM (OpenAI-compatible) ────────────────────────────────────
    nvidia_api_key: str
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "meta/llama-3.1-70b-instruct"
    nvidia_timeout: int = 60
    nvidia_max_retries: int = 4

    # ── LangSmith ─────────────────────────────────────────────────────────
    langsmith_api_key: str
    langsmith_project: str = "lexguard"
    langsmith_tracing: bool = True

    # ── Neon DB (PostgreSQL) ──────────────────────────────────────────────
    neon_database_url: str  # postgresql+asyncpg://user:pass@host/db

    # ── RAG Pipeline ──────────────────────────────────────────────────────
    max_rag_retries: int = 3
    max_history_messages: int = 10
    retrieval_top_k: int = 8
    sufficiency_threshold: float = 0.7
    quality_threshold: float = 0.65

    # ── CORS ──────────────────────────────────────────────────────────────
    allowed_origins: list[str] = ["http://localhost:3000", "https://*.run.app"]

    # ── Upload ────────────────────────────────────────────────────────────
    max_upload_size_mb: int = 50

    @property
    def sync_database_url(self) -> str:
        """Synchronous URL for Alembic migrations."""
        return self.neon_database_url.replace("+asyncpg", "+psycopg2")

    @property
    def openai_client_kwargs(self) -> dict:
        return {
            "api_key": self.nvidia_api_key,
            "base_url": self.nvidia_base_url,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
