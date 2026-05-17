"""
LlamaParse document ingestion — direct REST API via httpx.

WHY NOT llama-cloud-services SDK:
  llama-cloud-services 0.6.x internally imports pydantic.v1 (Pydantic V1 compat shim).
  Pydantic V1 is broken on Python 3.14:
      UserWarning: Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.
      RuntimeError: no validator found for <class 'pydantic.v1.fields.UndefinedType'>
  Since our stack is Python 3.14 we bypass the SDK and hit the LlamaParse REST API
  directly with httpx — this is exactly what the SDK does internally.

REST API reference: https://docs.llamaindex.ai/llamaparse/parse/guides/api-reference/

Flow:
    1. POST /api/parsing/upload  →  { id: job_id }
    2. Poll GET /api/parsing/job/{job_id}  until status == "SUCCESS"
    3. GET /api/parsing/job/{job_id}/result/markdown  →  { markdown: "..." }
    4. Split by page separator and wrap each page in a LlamaIndex Document

Supports all formats: PDF, DOCX, DOC, TXT, HTML, PPTX, XLSX, RTF, ODT, MD.
"""

import asyncio
import logging
import tempfile
import os
from pathlib import Path

import httpx
from llama_index.core import Document as LlamaDocument

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

LLAMAPARSE_BASE_URL = "https://api.cloud.llamaindex.ai"
_POLL_INTERVAL_S = 3      # seconds between job status polls
_MAX_POLL_ATTEMPTS = 100  # 5 minutes max

# LlamaParse page separator in markdown output
_PAGE_SEP = "\n---\n"

# Legal-domain parsing instruction
_LEGAL_INSTRUCTION = (
    "This is a legal document (contract, offer letter, policy, or terms of service). "
    "Extract all text faithfully. Preserve clause numbering, section headers, and "
    "paragraph structure. Mark any tables clearly. Do not summarize."
)

SUPPORTED_MIME_TYPES: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "text/plain": ".txt",
    "text/html": ".html",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/rtf": ".rtf",
    "application/vnd.oasis.opendocument.text": ".odt",
    "text/markdown": ".md",
}

SUPPORTED_EXTENSIONS = set(SUPPORTED_MIME_TYPES.values())


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.llamaparse_api_key}"}


async def _upload_file(
    client: httpx.AsyncClient,
    file_bytes: bytes,
    filename: str,
    ext: str,
) -> str:
    """Upload file to LlamaParse and return the job ID."""
    response = await client.post(
        f"{LLAMAPARSE_BASE_URL}/api/parsing/upload",
        headers=_auth_headers(),
        files={"file": (filename, file_bytes, "application/octet-stream")},
        data={
            "language": "en",
            "result_type": "markdown",
            "parsing_instruction": _LEGAL_INSTRUCTION,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    job_id: str = response.json()["id"]
    logger.info(f"LlamaParse job started: {job_id}")
    return job_id


async def _wait_for_job(client: httpx.AsyncClient, job_id: str) -> None:
    """Poll until the job status is SUCCESS or raise on ERROR."""
    for attempt in range(_MAX_POLL_ATTEMPTS):
        await asyncio.sleep(_POLL_INTERVAL_S)
        resp = await client.get(
            f"{LLAMAPARSE_BASE_URL}/api/parsing/job/{job_id}",
            headers=_auth_headers(),
            timeout=30.0,
        )
        resp.raise_for_status()
        status: str = resp.json().get("status", "")
        logger.debug(f"LlamaParse job {job_id}: status={status} (attempt {attempt + 1})")

        if status == "SUCCESS":
            return
        if status in ("ERROR", "CANCELLED"):
            raise RuntimeError(
                f"LlamaParse job {job_id} failed with status: {status}"
            )

    raise TimeoutError(
        f"LlamaParse job {job_id} did not complete within "
        f"{_MAX_POLL_ATTEMPTS * _POLL_INTERVAL_S}s"
    )


async def _fetch_markdown(client: httpx.AsyncClient, job_id: str) -> str:
    """Fetch the markdown result for a completed job."""
    resp = await client.get(
        f"{LLAMAPARSE_BASE_URL}/api/parsing/job/{job_id}/result/markdown",
        headers=_auth_headers(),
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json().get("markdown", "")


def _split_into_documents(
    markdown: str,
    filename: str,
    mime_type: str,
) -> list[LlamaDocument]:
    """
    Split the full markdown string into per-page LlamaIndex Documents.
    LlamaParse separates pages with '\\n---\\n' in its markdown output.
    """
    pages = [p.strip() for p in markdown.split(_PAGE_SEP) if p.strip()]
    if not pages:
        pages = [markdown.strip()]

    total = len(pages)
    docs = []
    for i, page_text in enumerate(pages):
        doc = LlamaDocument(
            text=page_text,
            metadata={
                "source_file": filename,
                "mime_type": mime_type,
                "page_number": i + 1,
                "total_pages": total,
            },
        )
        docs.append(doc)
    return docs


async def parse_document(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> tuple[list[LlamaDocument], int]:
    """
    Parse a document using the LlamaParse REST API directly.

    Returns:
        (list[LlamaDocument], page_count)
        Each Document represents one page with markdown text + source metadata.
    """
    ext = SUPPORTED_MIME_TYPES.get(mime_type) or Path(filename).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: '{mime_type}' / '{ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    logger.info(
        f"Parsing '{filename}' ({len(file_bytes) / 1024:.1f} KB) "
        f"via LlamaParse REST API (ext={ext})"
    )

    async with httpx.AsyncClient() as client:
        job_id = await _upload_file(client, file_bytes, filename, ext)
        await _wait_for_job(client, job_id)
        markdown = await _fetch_markdown(client, job_id)

    docs = _split_into_documents(markdown, filename, mime_type)
    page_count = len(docs)
    logger.info(f"✅ Parsed {page_count} page(s) from '{filename}'")
    return docs, page_count
