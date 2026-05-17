"""
SemanticSplitterNodeParser — clause-aware semantic chunking.
Uses BGE embeddings via HF Inference API as the similarity model.

Per the official LlamaIndex docs (developers.llamaindex.ai/python/examples/node_parsers/semantic_chunking/):
  - SemanticSplitterNodeParser is SYNCHRONOUS — it calls _get_text_embeddings() internally.
  - Running asyncio.get_event_loop().run_until_complete() from inside FastAPI's already-running
    event loop raises "This event loop is already running."
  - Fix: run the synchronous HF HTTP call in a ThreadPoolExecutor so the event loop is not blocked,
    and bridge sync↔async correctly using run_in_executor.

Import:
    pip install llama-index-core
    (no llama-index-embeddings-huggingface needed — we call HF Inference API directly via httpx)
"""

import asyncio
import logging
import concurrent.futures
from functools import partial

from huggingface_hub import InferenceClient
from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core.schema import TextNode
from llama_index.core.embeddings import BaseEmbedding
from tenacity import retry, stop_after_attempt, wait_exponential
from llama_index.core.embeddings import BaseEmbedding

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Shared thread pool for blocking HF HTTP calls made by the synchronous splitter
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="hf-embed")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _sync_embed_batch(batch: list[str], client: InferenceClient) -> list[list[float]]:
    res = client.feature_extraction(batch, model=settings.embedding_model)
    
    if hasattr(res, "tolist"):
        res = res.tolist()
        
    if batch and isinstance(res[0], float):
        return [res]
    return res


def _sync_embed(texts: list[str]) -> list[list[float]]:
    """
    Synchronous HF Inference API call — safe to run in a thread.
    SemanticSplitterNodeParser calls this from its own (non-async) code path.
    Uses the official InferenceClient and batches requests to avoid 500 errors.
    """
    if not texts:
        return []
        
    client = InferenceClient(token=settings.hf_api_key)
    all_embeddings = []
    BATCH_SIZE = 32
    
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        batch_result = _sync_embed_batch(batch, client)
        all_embeddings.extend(batch_result)
        
    return all_embeddings


class HFEmbedAdapter(BaseEmbedding):
    """
    Bridges HF Inference API into LlamaIndex's BaseEmbedding interface.

    SemanticSplitterNodeParser is fully synchronous — it directly calls
    _get_text_embedding / _get_text_embeddings. We implement those with
    plain synchronous httpx calls (safe, since the splitter runs in a
    thread via run_in_executor when called from async context).

    The async variants (_aget_*) delegate to the async embedder for use
    in the rest of the pipeline (e.g. query embedding at query time).
    """

    model_name: str = settings.embedding_model

    # ── Sync methods — called by SemanticSplitterNodeParser ───────────────

    def _get_query_embedding(self, query: str) -> list[float]:
        return _sync_embed([query])[0]

    def _get_text_embedding(self, text: str) -> list[float]:
        return _sync_embed([text])[0]

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Called in batches by SemanticSplitterNodeParser to compute
        sentence-pair similarities for breakpoint detection.
        """
        return _sync_embed(texts)

    # ── Async methods — used elsewhere in the pipeline ────────────────────

    async def _aget_query_embedding(self, query: str) -> list[float]:
        from app.services.ingestion.embedder import embed_single
        return await embed_single(query)

    async def _aget_text_embedding(self, text: str) -> list[float]:
        from app.services.ingestion.embedder import embed_single
        return await embed_single(text)

    async def _aget_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        from app.services.ingestion.embedder import embed_texts
        return await embed_texts(texts)


def _build_splitter() -> SemanticSplitterNodeParser:
    """
    Construct the SemanticSplitterNodeParser exactly as shown in the docs:

        splitter = SemanticSplitterNodeParser(
            buffer_size=1,
            breakpoint_percentile_threshold=95,
            embed_model=embed_model,
        )

    buffer_size=1               — compare adjacent sentence pairs
    breakpoint_percentile_threshold=95 — only split at the top 5% of
                                         semantic dissimilarity (keeps
                                         legal clauses together)
    """
    embed_model = HFEmbedAdapter()
    return SemanticSplitterNodeParser(
        buffer_size=1,
        breakpoint_percentile_threshold=95,  # Docs recommend 95; higher = fewer, larger chunks
        embed_model=embed_model,
    )


async def chunk_documents(
    docs: list[LlamaDocument],
    doc_id: str,
    source_name: str,
) -> list[TextNode]:
    """
    Chunk a list of LlamaDocuments into semantic TextNodes.

    SemanticSplitterNodeParser is synchronous, so we run it in a
    ThreadPoolExecutor to avoid blocking FastAPI's event loop.
    """
    splitter = _build_splitter()

    loop = asyncio.get_running_loop()
    # run_in_executor lets the sync splitter (and its sync HF calls) run
    # in a thread while the event loop remains unblocked.
    nodes: list[TextNode] = await loop.run_in_executor(
        _EXECUTOR,
        partial(splitter.get_nodes_from_documents, docs),
    )

    # Enrich metadata on each node
    for i, node in enumerate(nodes):
        node.metadata.update({
            "doc_id": doc_id,
            "source": source_name,
            "chunk_index": i,
        })
        node.excluded_embed_metadata_keys = ["chunk_index"]
        node.excluded_llm_metadata_keys = ["chunk_index"]

    logger.info(
        f"✅ Chunked {len(docs)} page(s) → {len(nodes)} semantic nodes "
        f"(model={settings.embedding_model}, threshold=95)"
    )
    return nodes
