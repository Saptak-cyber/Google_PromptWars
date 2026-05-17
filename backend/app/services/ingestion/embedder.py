"""
HuggingFace Inference API — BGE embedding service.
Model and dimensions are configurable via env vars.
"""

import logging
import asyncio
from typing import Optional

from huggingface_hub import AsyncInferenceClient
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

BATCH_SIZE = 32  # HF free tier limit


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a single batch via official HF Inference Client."""
    client = AsyncInferenceClient(token=settings.hf_api_key)
    res = await client.feature_extraction(texts, model=settings.embedding_model)
    
    # HF returns a numpy array or list depending on the input
    if hasattr(res, "tolist"):
        res = res.tolist()
        
    if texts and isinstance(res[0], float):
        return [res]
    return res


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts using HF Inference API.
    Batches automatically, returns list of float vectors.
    """
    if not texts:
        return []

    all_embeddings: list[list[float]] = []
    batches = [texts[i : i + BATCH_SIZE] for i in range(0, len(texts), BATCH_SIZE)]

    tasks = [_embed_batch(batch) for batch in batches]
    results = await asyncio.gather(*tasks)
    for batch_result in results:
        # batch_result is guaranteed to be list[list[float]] by _embed_batch
        all_embeddings.extend(batch_result)

    logger.info(
        f"✅ Embedded {len(texts)} texts using {settings.embedding_model} "
        f"(dim={settings.embedding_dimensions})"
    )
    return all_embeddings


async def embed_single(text: str) -> list[float]:
    """Convenience wrapper for a single text."""
    results = await embed_texts([text])
    return results[0]
