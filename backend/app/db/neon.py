"""
Neon DB — Async SQLAlchemy engine + session factory.
Uses asyncpg driver for non-blocking I/O with Neon's serverless PostgreSQL.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    pass


# Create the async engine with connection pooling tuned for Cloud Run
engine = create_async_engine(
    settings.neon_database_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,          # Validate connections before use (important for Neon)
    pool_recycle=300,            # Recycle connections every 5 min (Neon timeout safety)
    connect_args={
        "server_settings": {"application_name": "lexguard"},
        "ssl": "require",
    },
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup (idempotent)."""
    from app.db import models  # noqa — ensure models are registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables verified/created")
