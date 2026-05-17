"""
Ingest router — document upload, parsing, chunking, and Qdrant indexing.
Supports all formats via LlamaParse.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.neon import get_db
from app.db.models import Document
from app.services.ingestion.parser import parse_document, SUPPORTED_EXTENSIONS
from app.services.ingestion.chunker import chunk_documents
from app.services.retrieval.qdrant_store import upsert_nodes, delete_by_doc_id
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    doc_name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and index a legal document.

    Supported formats: PDF, DOCX, DOC, TXT, HTML, PPTX, XLSX, RTF, ODT, MD
    """
    # Validate size
    file_bytes = await file.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > settings.max_upload_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Max: {settings.max_upload_size_mb} MB",
        )

    doc_id = str(uuid.uuid4())
    name = doc_name or file.filename or "Unnamed Document"
    mime_type = file.content_type or "application/octet-stream"

    logger.info(f"Ingesting '{name}' ({size_mb:.2f} MB, {mime_type})")

    try:
        # Step 1: Parse with LlamaParse
        docs, page_count = await parse_document(file_bytes, file.filename, mime_type)

        # Step 2: Semantic chunking
        nodes = await chunk_documents(docs, doc_id=doc_id, source_name=name)

        # Step 3: Embed + upsert to Qdrant
        upserted = await upsert_nodes(nodes)

        # Step 4: Persist document metadata to Neon DB
        db_doc = Document(
            id=doc_id,
            name=name,
            mime_type=mime_type,
            chunk_count=upserted,
            page_count=page_count,
        )
        db.add(db_doc)
        await db.commit()

        logger.info(f"✅ Indexed '{name}': {page_count} pages, {upserted} chunks")
        return JSONResponse({
            "doc_id": doc_id,
            "name": name,
            "pages": page_count,
            "chunks": upserted,
            "status": "indexed",
        })

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Ingestion failed for '{name}': {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/supported-formats")
async def get_supported_formats():
    """Return list of supported file formats."""
    return {"supported_extensions": sorted(SUPPORTED_EXTENSIONS)}
