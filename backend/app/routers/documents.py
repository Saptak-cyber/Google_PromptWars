"""
Documents router — list and delete indexed documents.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.db.neon import get_db
from app.db.models import Document
from app.services.retrieval.qdrant_store import delete_by_doc_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List all indexed documents."""
    result = await db.execute(select(Document).order_by(Document.uploaded_at.desc()))
    docs = result.scalars().all()
    return {
        "documents": [
            {
                "doc_id": d.id,
                "name": d.name,
                "mime_type": d.mime_type,
                "chunk_count": d.chunk_count,
                "page_count": d.page_count,
                "uploaded_at": d.uploaded_at.isoformat(),
            }
            for d in docs
        ]
    }


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a document from Qdrant and Neon DB."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove vectors from Qdrant
    await delete_by_doc_id(doc_id)

    # Remove from Neon DB (cascades to conversations + messages)
    await db.execute(delete(Document).where(Document.id == doc_id))
    await db.commit()

    return {"status": "deleted", "doc_id": doc_id}
