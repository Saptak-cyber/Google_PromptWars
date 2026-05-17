# LexGuard Backend

> **Adversarial multi-agent RAG pipeline for legal contract intelligence**

FastAPI backend powering LexGuard — a system that reads legal documents, runs a 7-step self-correcting agentic loop, and delivers structured risk verdicts through a real-time streaming debate between three AI agents.

---

## Architecture Overview

```
Upload (PDF/DOCX/…)
        │
        ▼
  LlamaParse REST API          ← direct httpx calls (no SDK)
        │
        ▼
 SemanticSplitter (LlamaIndex) ← BGE embeddings via HF Inference API
        │
        ▼
   Qdrant Cloud                ← vector store for semantic search
        │
  ┌─────┴──────────────────────────────────────┐
  │          7-Step Agentic RAG Loop            │
  │  1. Condense query (conversation history)   │
  │  2. Legal-expand query                      │
  │  3. HyDE retrieval                          │
  │  4. Sufficiency check (retry if needed)     │
  │  5. Prosecutor ⚔️  Devil's Advocate debate  │
  │  6. Judge synthesis → structured verdict    │
  │  7. Quality audit (retry loop)              │
  └─────────────────────────────────────────────┘
        │
        ▼
   SSE Stream → Next.js frontend
        │
   Neon DB (PostgreSQL)        ← conversation history via LangChain
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | FastAPI + Uvicorn (async, multi-worker) |
| **Document Parsing** | LlamaParse REST API (direct httpx — no SDK, Python 3.14 compat) |
| **Chunking** | `SemanticSplitterNodeParser` (LlamaIndex), `buffer_size=1`, `threshold=95` |
| **Embeddings** | `BAAI/bge-base-en-v1.5` via HuggingFace Inference API |
| **Vector Store** | Qdrant Cloud |
| **LLM** | NVIDIA NIM (OpenAI-compatible API) — configurable model |
| **Orchestration** | LangChain (query rewriting templates, prompt chaining) |
| **Conversation History** | Neon DB (PostgreSQL) via `langchain-postgres` |
| **Observability** | LangSmith (tracing every RAG step) |
| **Streaming** | Server-Sent Events (SSE) via FastAPI `StreamingResponse` |
| **Deployment** | Docker → Google Cloud Run |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, CORS, lifespan, router registration
│   ├── config.py                # Pydantic-settings — all env vars in one place
│   ├── db/
│   │   ├── neon.py              # Async SQLAlchemy engine (Neon PostgreSQL)
│   │   ├── models.py            # ORM models: Document, Conversation, Message
│   │   └── conversation_store.py # LangChain PostgresChatMessageHistory wrapper
│   ├── routers/
│   │   ├── ingest.py            # POST /ingest/upload — multi-format file upload
│   │   ├── query.py             # POST /query/stream — SSE streaming RAG endpoint
│   │   └── documents.py         # GET/DELETE /documents — document management
│   ├── services/
│   │   ├── ingestion/
│   │   │   ├── parser.py        # LlamaParse REST API (direct httpx, Python 3.14 safe)
│   │   │   ├── chunker.py       # SemanticSplitterNodeParser + HFEmbedAdapter
│   │   │   └── embedder.py      # BGE embeddings via HF Inference API
│   │   ├── retrieval/
│   │   │   └── qdrant_store.py  # Qdrant async client — upsert, search, filter
│   │   ├── query/
│   │   │   └── rewriter.py      # 3-stage query rewrite: condense → expand → HyDE
│   │   └── agents/
│   │       ├── rag_pipeline.py      # Master 7-step orchestrator
│   │       ├── prosecutor_agent.py  # Adversarial risk analysis agent
│   │       ├── devils_advocate.py   # Clause defence agent
│   │       ├── judge_agent.py       # Synthesis + structured verdict
│   │       ├── sufficiency_checker.py
│   │       ├── query_enhancer.py
│   │       └── quality_evaluator.py
│   └── utils/
│       └── streaming.py         # SSE event helpers
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Setup

### 1. Prerequisites

- Python **3.11** recommended (Docker image uses 3.11-slim)
- Python **3.14** also works locally — all packages have been updated for 3.14 compat
- A `.env` file (copy from `.env.example`)

### 2. Clone & Install

```bash
git clone <repo-url>
cd backend

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Environment Variables

Copy the template and fill in your keys:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `LLAMAPARSE_API_KEY` | From [cloud.llamaindex.ai](https://cloud.llamaindex.ai) |
| `HF_API_KEY` | HuggingFace Inference API key |
| `EMBEDDING_MODEL` | Default: `BAAI/bge-base-en-v1.5` |
| `EMBEDDING_DIMENSIONS` | Default: `768` |
| `QDRANT_URL` | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Qdrant API key |
| `QDRANT_COLLECTION` | Default: `lexguard_contracts` |
| `NVIDIA_API_KEY` | NVIDIA NIM API key (`nvapi-...`) |
| `NVIDIA_BASE_URL` | Default: `https://integrate.api.nvidia.com/v1` |
| `NVIDIA_MODEL` | Default: `meta/llama-3.1-70b-instruct` |
| `LANGSMITH_API_KEY` | LangSmith tracing key |
| `LANGSMITH_PROJECT` | Project name in LangSmith |
| `NEON_DATABASE_URL` | Neon PostgreSQL connection string (asyncpg) |
| `ALLOWED_ORIGINS` | CORS origins JSON array, e.g. `["http://localhost:3000"]` |

### 4. Run Locally

```bash
uvicorn app.main:app --reload --port 8000
```

API docs available at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Endpoints

### Document Ingestion

```
POST /ingest/upload
Content-Type: multipart/form-data

Fields:
  file          — the document (PDF, DOCX, DOC, TXT, HTML, PPTX, XLSX, RTF, ODT, MD)
  conversation_id — optional UUID to associate the document with a conversation

Response:
  { "doc_id": "...", "filename": "...", "page_count": 12, "chunk_count": 47 }
```

### Streaming Query

```
POST /query/stream
Content-Type: application/json

Body:
  {
    "query": "Does this contract have a non-compete clause?",
    "conversation_id": "uuid",
    "doc_id": "uuid"            // optional — filter to one document
  }

Response: text/event-stream (SSE)

Event types:
  step_start    — pipeline step beginning (e.g. "Retrieving context")
  prosecutor    — streaming tokens from Prosecutor agent
  advocate      — streaming tokens from Devil's Advocate agent
  judge         — streaming tokens from Judge synthesis
  verdict       — final structured JSON verdict
  error         — pipeline error
  done          — stream complete
```

### Document Management

```
GET    /documents                    — list all indexed documents
DELETE /documents/{doc_id}           — remove document and its vectors
```

---

## Ingestion Pipeline Detail

### Why direct REST API for LlamaParse?

`llama-cloud-services` SDK internally uses `pydantic.v1` which is completely broken on Python 3.14. We call the LlamaParse REST API directly via `httpx`:

```
1. POST /api/parsing/upload   →  job_id
2. Poll GET /api/parsing/job/{id} until status == "SUCCESS"
3. GET /api/parsing/job/{id}/result/markdown  →  full markdown text
4. Split by page separator (\n---\n) → LlamaIndex Documents
```

### Why SemanticSplitterNodeParser?

Legal documents have variable clause lengths. Fixed-size chunking splits mid-clause. The semantic splitter uses sentence-pair embedding similarity to find natural semantic breakpoints:

```python
SemanticSplitterNodeParser(
    buffer_size=1,                    # compare adjacent sentence pairs
    breakpoint_percentile_threshold=95, # only split at top 5% dissimilarity
    embed_model=HFEmbedAdapter(),     # BGE via HF Inference API
)
```

`SemanticSplitterNodeParser` is synchronous internally, so chunking runs in a `ThreadPoolExecutor` to avoid blocking FastAPI's async event loop.

---

## Docker

```bash
# Build
docker build -t lexguard-backend .

# Run
docker run -p 8080:8080 --env-file .env lexguard-backend
```

The Dockerfile uses `python:3.11-slim`, runs as a non-root user, and starts Uvicorn with 2 workers optimised for Cloud Run concurrency.

---

## Deployment (Google Cloud Run)

See `gcp/` at the repo root for:
- `gcp/setup.sh` — API enablement, Artifact Registry, Secret Manager population
- `gcp/cloudbuild.yaml` — CI/CD pipeline (parallel build + deploy)

Quick deploy:

```bash
# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Run setup (one-time)
bash gcp/setup.sh

# Trigger build
gcloud builds submit --config gcp/cloudbuild.yaml
```

After the first deploy, set `NEXT_PUBLIC_API_URL` in `cloudbuild.yaml` to the Cloud Run backend URL.

---

## Observability

Every RAG pipeline execution is traced in LangSmith:

- Query rewriting steps (condense → expand → HyDE)
- Retrieval calls and retrieved chunk counts
- Prosecutor / Advocate / Judge agent token streams
- Quality audit scores and retry decisions

Set `LANGSMITH_TRACING=true` in `.env` to enable. View traces at [smith.langchain.com](https://smith.langchain.com).

---

## Python 3.14 Compatibility Notes

If running locally on Python 3.14 (the system default on newer Macs), all packages in `requirements.txt` are unpinned to allow pip to resolve 3.14-compatible wheels:

| Issue | Fix applied |
|---|---|
| `pydantic-core 2.20.1` — PyO3 0.22 only supports Python ≤ 3.13 | Upgraded to `pydantic>=2.10.6` (uses PyO3 0.23+) |
| `asyncpg 0.29.0` — no Python 3.14 wheel | Upgraded to `asyncpg>=0.30.0` |
| `psycopg2-binary` — not needed; langchain-postgres uses psycopg3 | Replaced with `psycopg[binary]>=3.2.0` |
| `llama-cloud-services` — uses `pydantic.v1` broken on 3.14 | Removed; use direct REST API via httpx |

> **For production Docker builds** the Dockerfile uses `python:3.11-slim` — no compatibility issues.
