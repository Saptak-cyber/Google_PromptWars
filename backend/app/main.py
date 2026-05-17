"""
LexGuard FastAPI application entry point.
Registers routers, configures CORS, sets up LangSmith tracing on startup.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db.neon import init_db
from app.routers import ingest, query, documents

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("🚀 LexGuard starting up...")

    # Configure LangSmith tracing
    if settings.langsmith_tracing:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
        logger.info(f"✅ LangSmith tracing enabled → project: {settings.langsmith_project}")

    # Initialize Neon DB (run Alembic migrations)
    await init_db()
    logger.info("✅ Neon DB initialized")

    yield

    logger.info("👋 LexGuard shutting down...")


app = FastAPI(
    title="LexGuard API",
    description="AI Rights & Contract Intelligence System — Adversarial Multi-Agent RAG",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────
app.include_router(ingest.router, prefix="/api", tags=["Ingestion"])
app.include_router(query.router, prefix="/api", tags=["Query"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])


# ── Health ────────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
async def health_check():
    return JSONResponse({"status": "ok", "service": "lexguard-backend", "version": "1.0.0"})


@app.get("/", tags=["Root"])
async def root():
    return {"message": "LexGuard API — visit /docs for Swagger UI"}
