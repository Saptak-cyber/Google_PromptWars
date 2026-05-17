"""
Qdrant Cloud vector store — upsert and similarity search.
Collection is created automatically with the right dimensions on first use.
"""

import logging
import uuid
from typing import Optional

from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
)
from llama_index.core.schema import TextNode

from app.config import get_settings
from app.services.ingestion.embedder import embed_texts, embed_single

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=30,
    )


async def ensure_collection():
    """Create the Qdrant collection if it doesn't exist."""
    client = _get_client()
    collections = await client.get_collections()
    names = [c.name for c in collections.collections]
    if settings.qdrant_collection not in names:
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=settings.embedding_dimensions,
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"✅ Created Qdrant collection '{settings.qdrant_collection}'")
    await client.close()


async def upsert_nodes(nodes: list[TextNode]) -> int:
    """
    Embed and upsert a list of TextNodes into Qdrant.
    Returns the number of points upserted.
    """
    await ensure_collection()

    texts = [node.get_content() for node in nodes]
    embeddings = await embed_texts(texts)

    points = []
    for node, vector in zip(nodes, embeddings):
        points.append(
            PointStruct(
                id=node.node_id or str(uuid.uuid4()),
                vector=vector,
                payload={
                    "text": node.get_content(),
                    "doc_id": node.metadata.get("doc_id"),
                    "source": node.metadata.get("source"),
                    "page_number": node.metadata.get("page_number"),
                    "chunk_index": node.metadata.get("chunk_index"),
                    "mime_type": node.metadata.get("mime_type"),
                },
            )
        )

    client = _get_client()
    await client.upsert(
        collection_name=settings.qdrant_collection,
        points=points,
        wait=True,
    )
    await client.close()

    logger.info(f"✅ Upserted {len(points)} vectors into Qdrant")
    return len(points)


async def search(
    query_text: str,
    top_k: Optional[int] = None,
    doc_id_filter: Optional[str] = None,
) -> list[dict]:
    """
    Embed query and perform cosine similarity search in Qdrant.
    Optionally filter by doc_id.

    Returns list of {text, score, metadata} dicts.
    """
    k = top_k or settings.retrieval_top_k
    query_vector = await embed_single(query_text)

    qdrant_filter = None
    if doc_id_filter:
        qdrant_filter = Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id_filter))]
        )

    client = _get_client()
    results = await client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        limit=k,
        query_filter=qdrant_filter,
        with_payload=True,
        score_threshold=0.35,   # Minimum relevance threshold
    )
    await client.close()

    return [
        {
            "text": r.payload.get("text", ""),
            "score": r.score,
            "doc_id": r.payload.get("doc_id"),
            "source": r.payload.get("source"),
            "page_number": r.payload.get("page_number"),
            "chunk_index": r.payload.get("chunk_index"),
        }
        for r in results
    ]


async def delete_by_doc_id(doc_id: str):
    """Delete all vectors for a given document."""
    client = _get_client()
    await client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        ),
    )
    await client.close()
    logger.info(f"✅ Deleted vectors for doc_id={doc_id}")
