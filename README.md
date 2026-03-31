# Tax Knowledge Base API

A FastAPI-powered RESTful backend for managing a **Tax Knowledge Base** system. It supports hybrid RAG (Retrieval-Augmented Generation) search over tax documents, document ingestion via file upload / web scraping / external API push, governance workflows, and a full admin dashboard, all backed by PostgreSQL, Apache Solr, Azure Blob Storage, and OpenAI embeddings.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | FastAPI 0.109+ |
| **Language** | Python 3.12+ |
| **Database (relational)** | PostgreSQL via SQLAlchemy 2.0 (async, asyncpg) |
| **Search engine** | Apache Solr (BM25 + vector) |
| **Blob storage** | Azure Blob Storage |
| **Task queue** | Celery 5.6+ with Redis broker |
| **Embeddings / LLM** | OpenAI (`text-embedding-3-small`, `gpt-4o-mini`) |
| **PDF / Doc parsing** | pdfplumber, PyMuPDF, python-docx, Unstructured |
| **Text splitting** | LangChain text-splitters, tiktoken |
| **Web scraping** | httpx, BeautifulSoup4, lxml |
| **Migrations** | Alembic |
| **Validation** | Pydantic v2, pydantic-settings |
| **Server** | Uvicorn (ASGI) |

---

## Getting Started

### Prerequisites

| Requirement | Version |
|---|---|
| Python | >= 3.12 |
| PostgreSQL | 14+ recommended |
| Apache Solr | 9.x (collections: `tax_documents`, `tax_chunks`) |
| Redis | 6+ (for Celery broker/backend) |
| Azure Blob Storage | An active storage account (optional for local dev) |
| OpenAI API key | Required for embeddings and document classification |

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd everleagues-tax-kb

# Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies (using uv or pip)
pip install -e .
# or
uv sync
```

### Environment Variables

Create a `.env` file in the project root. All variables are loaded via `pydantic-settings` (case-insensitive).

| Variable | Type | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | string | `postgresql://taxkb_user:password@localhost:5432/tax_kb` | PostgreSQL connection URL |
| `DATABASE_ECHO` | bool | `false` | Log all SQL queries |
| `DATABASE_POOL_SIZE` | int | `10` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | int | `20` | Max overflow connections beyond pool size |
| `SOLR_BASE_URL` | string | `http://localhost:8983/solr` | Solr base URL |
| `SOLR_USERNAME` | string | `null` | Solr basic-auth username |
| `SOLR_PASSWORD` | string | `null` | Solr basic-auth password |
| `SOLR_DOCUMENTS_COLLECTION` | string | `tax_documents` | Solr collection for documents |
| `SOLR_CHUNKS_COLLECTION` | string | `tax_chunks` | Solr collection for chunks |
| `AZURE_STORAGE_CONNECTION_STRING` | string | `null` | Azure Blob Storage connection string |
| `AZURE_STORAGE_ACCOUNT_NAME` | string | `null` | Azure storage account name |
| `AZURE_STORAGE_ACCOUNT_KEY` | string | `null` | Azure storage account key |
| `AZURE_CONTAINER_RAW` | string | `raw-documents` | Container for raw uploaded files |
| `AZURE_CONTAINER_PROCESSED` | string | `processed-documents` | Container for processed files |
| `AZURE_CONTAINER_UPLOADS` | string | `uploads` | Container for direct uploads |
| `AZURE_CONTAINER_API_PUSHED` | string | `api-pushed` | Container for API-pushed files |
| `OPENAI_API_KEY` | string | `null` | OpenAI API key for embeddings and classification |
| `EMBEDDING_MODEL` | string | `text-embedding-3-small` | OpenAI embedding model name |
| `EMBEDDING_DIMENSION` | int | `1536` | Embedding vector dimension |
| `CLASSIFIER_LLM_MODEL` | string | `gpt-4o-mini` | LLM model for document classification |
| `CLASSIFIER_LLM_TEMPERATURE` | float | `0.1` | Classification LLM temperature |
| `CLASSIFIER_LLM_MAX_TOKENS` | int | `600` | Classification LLM max tokens |
| `BM25_WEIGHT` | float | `0.3` | Hybrid search BM25 weight (alpha) |
| `VECTOR_WEIGHT` | float | `0.5` | Hybrid search vector weight (beta) |
| `AUTHORITY_WEIGHT` | float | `0.4` | Hybrid search authority weight (gamma) |
| `API_HOST` | string | `0.0.0.0` | Uvicorn bind host |
| `API_PORT` | int | `8001` | Uvicorn bind port |
| `API_PREFIX` | string | `/api` | Global API route prefix |
| `DEBUG` | bool | `false` | Debug mode |
| `CORS_ORIGINS` | list[string] | `["http://localhost:8001", ...]` | Allowed CORS origins (JSON array) |
| `CORS_ALLOW_CREDENTIALS` | bool | `true` | CORS allow credentials |
| `CORS_ALLOW_METHODS` | list[string] | `["*"]` | CORS allowed methods |
| `CORS_ALLOW_HEADERS` | list[string] | `["*"]` | CORS allowed headers |
| `DEFAULT_PAGE_SIZE` | int | `20` | Default pagination page size |
| `MAX_PAGE_SIZE` | int | `100` | Maximum pagination page size |
| `SCRAPER_DEFAULT_DELAY` | float | `2.0` | Default delay between scrape requests (seconds) |
| `SCRAPER_DEFAULT_RPM` | int | `30` | Default max requests per minute |
| `SCRAPER_DEFAULT_TIMEOUT` | int | `30` | Scraper request timeout (seconds) |
| `SCRAPER_MAX_FILES_PER_SESSION` | int | `10000` | Max files per scrape session |
| `MAX_UPLOAD_SIZE_MB` | int | `50` | Maximum file upload size in MB |
| `ALLOWED_FILE_EXTENSIONS` | list[string] | `[".pdf", ".doc", ".docx", ".txt", ".xml", ".html", ".htm"]` | Allowed upload extensions |
| `PROCESS_UPLOADS_SYNC` | bool | `true` | Process uploads synchronously (false = Celery background) |
| `CELERY_BROKER_URL` | string | `redis://localhost:6379/0` | Celery broker URL |
| `CELERY_RESULT_BACKEND` | string | `redis://localhost:6379/1` | Celery result backend URL |
| `WORKER_CONCURRENCY` | int | `4` | Celery worker concurrency |
| `WORKER_MAX_RETRIES` | int | `3` | Max task retries |
| `WORKER_RETRY_DELAY` | int | `60` | Retry delay in seconds |
| `SCRAPE_TASK_SOFT_TIME_LIMIT` | int | `3600` | Celery soft time limit for scrape tasks (seconds) |
| `SCRAPE_TASK_TIME_LIMIT` | int | `3660` | Celery hard time limit for scrape tasks (seconds) |
| `NEO4J_URI` | string | `null` | Neo4j connection URI (optional) |
| `NEO4J_USERNAME` | string | `null` | Neo4j username (optional) |
| `NEO4J_PASSWORD` | string | `null` | Neo4j password (optional) |
| `NEO4J_DATABASE` | string | `neo4j` | Neo4j database name |
| `ONTOLOGY_OWL_URLS` | list[string] | `[]` | OWL/RDF ontology URLs for import |

### Running the Project

```bash
# Start the API server (development)
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Start a Celery worker (for background scraping/processing)
celery -A app.worker.celery_app worker --loglevel=info --concurrency=4
```

Once running, interactive API docs are available at:
- **Swagger UI**: `http://localhost:8001/api/docs`
- **ReDoc**: `http://localhost:8001/api/redoc`
- **OpenAPI JSON**: `http://localhost:8001/api/openapi.json`

---

## Project Structure

```
everleagues-tax-kb/
|-- main.py                          # FastAPI app entry point, lifespan, root routes
|-- pyproject.toml                   # Python project metadata and dependencies
|-- .env                             # Environment variables (not committed)
|
|-- app/
|   |-- __init__.py
|   |-- dependencies.py              # FastAPI dependency injection (DB session, services)
|   |
|   |-- config/
|   |   |-- __init__.py
|   |   |-- settings.py              # Pydantic-settings configuration class
|   |   |-- jurisdiction_config.py   # US state/city validation data
|   |   |-- jurisdictions.json       # Jurisdiction lookup dataset
|   |
|   |-- database/
|   |   |-- __init__.py
|   |   |-- base.py                  # SQLAlchemy Base, UUID and Timestamp mixins
|   |   |-- connection.py            # Async engine, session factory, init_db()
|   |
|   |-- db_models/                   # SQLAlchemy ORM models (PostgreSQL)
|   |   |-- __init__.py
|   |   |-- document_registry.py     # DocumentRegistry, DocumentBlob
|   |   |-- scrape_url.py            # ScrapeUrl
|   |   |-- scrape_job.py            # ScrapeJob, ScrapeJobLog
|   |   |-- path_rule.py             # PathRule
|   |   |-- discovered_page.py       # DiscoveredPage
|   |   |-- api_source.py            # ApiSource
|   |   |-- governance.py            # GovernanceTransition
|   |   |-- audit.py                 # AuditLog
|   |   |-- system.py                # SystemSetting
|   |
|   |-- models/                      # Pydantic request/response schemas
|   |   |-- __init__.py
|   |   |-- common.py                # Shared enums, FilterParams, pagination
|   |   |-- document.py              # Document CRUD schemas
|   |   |-- search.py                # RAG search request/response
|   |   |-- urls.py                  # URL management schemas
|   |   |-- dashboard.py             # Dashboard metrics schemas
|   |   |-- governance.py            # Governance log schemas
|   |   |-- audit.py                 # Audit log schemas
|   |   |-- upload.py                # File upload schemas
|   |   |-- discovery.py             # Page discovery / path rule schemas
|   |   |-- api_sources.py           # External API source schemas
|   |   |-- chunk.py                 # Chunk schemas
|   |
|   |-- routers/                     # FastAPI route handlers
|   |   |-- __init__.py
|   |   |-- search.py                # /api/search/*
|   |   |-- documents.py             # /api/documents/*
|   |   |-- dashboard.py             # /api/dashboard/*
|   |   |-- governance.py            # /api/governance/*
|   |   |-- urls.py                  # /api/urls/*
|   |   |-- discovery.py             # /api/urls/{id}/discover/*, path-rules
|   |   |-- audit.py                 # /api/audit/*
|   |   |-- upload.py                # /api/upload
|   |   |-- api_push.py              # /api/push/*
|   |   |-- api_sources.py           # /api/sources/*
|   |
|   |-- services/                    # Business logic layer
|   |   |-- __init__.py
|   |   |-- solr_service.py          # Solr HTTP client
|   |   |-- search_service.py        # Hybrid RAG search logic
|   |   |-- document_service.py      # Document CRUD via Solr
|   |   |-- chunk_service.py         # Chunk management
|   |   |-- text_chunker.py          # Text splitting and chunking
|   |   |-- embedding_service.py     # OpenAI embedding generation
|   |   |-- document_classifier_service.py  # LLM-based metadata extraction
|   |   |-- ingestion_service.py     # End-to-end document ingestion pipeline
|   |   |-- blob_storage_service.py  # Azure Blob Storage operations
|   |   |-- url_db_service.py        # Scrape URL CRUD (PostgreSQL)
|   |   |-- scrape_service.py        # Web scraping logic
|   |   |-- scrape_job_service.py    # Scrape job tracking
|   |   |-- discovery_service.py     # Site discovery / crawling
|   |   |-- discovered_page_service.py  # Discovered page management
|   |   |-- path_rule_service.py     # Path include/exclude rules
|   |   |-- document_registry_service.py  # Document registry (PostgreSQL)
|   |   |-- api_source_service.py    # External API source management
|   |   |-- audit_log_service.py     # Audit log writes
|   |   |-- file_parser/             # File parsing subsystem
|   |   |   |-- __init__.py
|   |   |   |-- service.py           # Parser orchestrator
|   |   |   |-- loaders.py           # PDF, DOCX, HTML, TXT loaders
|   |   |   |-- result.py            # Parse result data class
|   |   |   |-- exceptions.py        # Parser-specific exceptions
|   |
|   |-- worker/                      # Celery background tasks
|   |   |-- celery_app.py            # Celery app configuration
|   |   |-- tasks.py                 # Task definitions (scrape, process_document)
|   |
|   |-- utils/
|   |   |-- __init__.py
|   |   |-- validators.py            # URL, authority level, and query validators
|   |
|   |-- prompts/
|       |-- __init__.py              # LLM prompt templates
```

---

## API Documentation

**Base URL**: `http://localhost:8001`
**API Prefix**: `/api` (all grouped endpoints live under this prefix)

### Root

---

### `GET /`

**Description:** Returns API identity and documentation links.

**Auth required:** No

**Success Response (200):**
```json
{
  "name": "Tax Knowledge Base API",
  "version": "1.0.0",
  "docs": "/api/docs",
  "redoc": "/api/redoc",
  "openapi": "/api/openapi.json"
}
```

---

### `GET /health`

**Description:** Liveness check. Reports Solr collection health.

**Auth required:** No

**Success Response (200):**
```json
{
  "status": "healthy",
  "solr_documents": true,
  "solr_chunks": true,
  "version": "1.0.0"
}
```

**Degraded Response (200):**
```json
{
  "status": "unhealthy",
  "solr_documents": false,
  "solr_chunks": false,
  "version": "1.0.0",
  "error": "Connection refused"
}
```

---

### Search

---

### `POST /api/search/rag`

**Description:** Hybrid RAG search combining BM25 keyword matching, vector similarity, and authority-level weighting. Returns ranked chunks and source documents.

**Auth required:** No

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string | Yes | Search query text (min length 1) |
| `filters` | object | No | Filter parameters (see FilterParams below) |
| `filters.jurisdiction` | string | No | `federal`, `state`, or `local` |
| `filters.state` | string | No | US state code (e.g. `CA`, `NY`) |
| `filters.city` | string | No | City name |
| `filters.tax_year` | int | No | Tax year |
| `filters.authority_level` | int | No | Authority level (1-6) |
| `filters.governance_state` | string | No | `Draft`, `Under Review`, `Published`, `Deprecated`, `Archived` |
| `filters.doc_type` | string | No | Document type filter |
| `filters.source_domain` | string | No | Source domain filter |
| `filters.needs_human_review` | bool | No | Filter by review status |
| `search_quality_controls` | object | No | Tuning parameters |
| `search_quality_controls.retrieval_mode` | string | No | `hybrid` (default), `vector`, or `bm25` |
| `search_quality_controls.authority_weight_control` | float | No | Authority weight 0.0-1.0 (default 0.5) |
| `search_quality_controls.semantic_lexical_balance` | float | No | Semantic vs lexical balance 0.0-1.0 (default 0.5) |
| `search_quality_controls.top_k` | int | No | Number of results 1-100 (default 10) |

**Example Request:**
```json
{
  "query": "capital gains tax rate for 2024",
  "filters": {
    "jurisdiction": "federal",
    "tax_year": 2024
  },
  "search_quality_controls": {
    "retrieval_mode": "hybrid",
    "top_k": 10
  }
}
```

**Success Response (200):**
```json
{
  "query": "capital gains tax rate for 2024",
  "retrieved_chunks": [
    {
      "id": "chunk-uuid",
      "chunk_id": "doc-uuid_chunk_0",
      "document_name": "irs-pub-544.pdf",
      "content": "The tax rate on most net capital gain is no higher than 15%...",
      "relevance_score": 0.89,
      "authority_level": 1,
      "priority_rank": 1,
      "is_preferred": true,
      "tax_year": 2024,
      "jurisdiction": "federal",
      "source_url": "https://www.irs.gov/pub544",
      "source_domain": "irs.gov"
    }
  ],
  "source_documents": [
    {
      "id": "doc-uuid",
      "title": "IRS Publication 544",
      "jurisdiction": "federal",
      "authority_level": 1,
      "tax_year": 2024,
      "is_preferred": true,
      "chunks": []
    }
  ],
  "total_chunks": 1,
  "search_time_ms": 142.5,
  "retrieval_mode": "hybrid",
  "score_weights": { "alpha": 0.3, "beta": 0.5, "gamma": 0.4 }
}
```

| Status | Message |
|---|---|
| 500 | Internal search error |

---

### Documents

---

### `GET /api/documents`

**Description:** List documents from Solr with filtering and pagination.

**Auth required:** No

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `query` | string | No | Solr query (default `*:*`) |
| `jurisdiction` | string | No | Jurisdiction filter |
| `state` | string | No | State code filter |
| `city` | string | No | City filter |
| `tax_year` | int | No | Tax year filter |
| `authority_level` | int | No | Authority level 1-6 |
| `governance_state` | string | No | Governance state filter |
| `doc_type` | string | No | Document type filter |
| `needs_human_review` | bool | No | Review status filter |
| `page` | int | No | Page number (default 1) |
| `limit` | int | No | Items per page 1-100 (default 20) |
| `sort` | string | No | Sort field (default `uploadedDate desc`) |

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "doc-uuid",
      "name": "tax-form-1040.pdf",
      "title": "Form 1040 - Individual Income Tax Return",
      "jurisdiction": "federal",
      "governance_state": "Published",
      "chunk_count": 45,
      "sync_status": "synced",
      "index_status": "indexed",
      "uploaded_date": "2024-12-01T10:30:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 20,
  "pages": 8,
  "has_next": true,
  "has_prev": false
}
```

---

### `GET /api/documents/{document_id}`

**Description:** Get a single document by ID.

**Auth required:** No

**Path Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | Yes | Document ID |

**Success Response (200):** `DocumentResponse` object.

| Status | Message |
|---|---|
| 404 | Document not found |

---

### `POST /api/documents`

**Description:** Create a new document in Solr.

**Auth required:** No

**Request Body:** `DocumentCreate` schema -- includes all `DocumentBase` fields plus `size`, `knowledge_base_id`, and `source_type`.

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Document filename |
| `title` | string | No | Document title |
| `description` | string | No | Description |
| `source_url` | string | No | Source URL |
| `tags` | string[] | No | Tags |
| `doc_type` | string | No | Document type |
| `tax_year` | int | No | Tax year |
| `jurisdiction` | string | No | Jurisdiction level |
| `state` | string | No | State code |
| `city` | string | No | City name |
| `authority_level` | int | No | Authority level 1-6 |
| `size` | string | No | File size |
| `knowledge_base_id` | string | No | Knowledge base ID (default `default`) |
| `source_type` | string | No | `upload`, `scrape`, or `api` |

**Success Response (201):** `DocumentResponse` object.

---

### `PUT /api/documents/{document_id}`

**Description:** Update a document. Writes an audit log entry on success.

**Auth required:** No

**Path Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | Yes | Document ID |

**Request Body:** `DocumentUpdate` -- all fields optional.

**Success Response (200):** Updated `DocumentResponse`.

| Status | Message |
|---|---|
| 404 | Document not found |

---

### `DELETE /api/documents/{document_id}`

**Description:** Delete a document and all its chunks. Removes registry entry and writes audit log.

**Auth required:** No

**Path Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | Yes | Document ID |

**Success Response:** `204 No Content`

| Status | Message |
|---|---|
| 404 | Document not found |

---

### `GET /api/documents/{document_id}/chunks`

**Description:** Get paginated chunks for a document.

**Auth required:** No

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `page` | int | No | Page number (default 1) |
| `limit` | int | No | Items per page 1-1000 (default 20) |

**Success Response (200):**
```json
{
  "items": [],
  "total": 45,
  "page": 1,
  "limit": 20,
  "pages": 3,
  "has_next": true,
  "has_prev": false
}
```

---

### `PUT /api/documents/{document_id}/governance`

**Description:** Update the governance state of a document and record history.

**Auth required:** No

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `governance_state` | string | Yes | `Draft`, `Under Review`, `Published`, `Deprecated`, `Archived` |
| `changed_by` | string | Yes | User who made the change |
| `reason` | string | No | Reason for the change |

**Success Response (200):** Updated `DocumentResponse`.

| Status | Message |
|---|---|
| 404 | Document not found |

---

### `POST /api/documents/{document_id}/reprocess`

**Description:** Re-queue a failed document for reprocessing via Celery. Only works if the document is in `sync_failed` or `index_failed` status.

**Auth required:** No

**Success Response (200):**
```json
{
  "registry_id": "uuid",
  "status": "queued",
  "message": "Document queued for reprocessing"
}
```

| Status | Message |
|---|---|
| 404 | Document not found |

---

### `POST /api/documents/reprocess-failed`

**Description:** Bulk reprocess all failed documents (up to 1000).

**Auth required:** No

**Success Response (200):**
```json
{
  "queued_count": 5,
  "skipped_count": 0,
  "failed_ids": [],
  "message": "5 documents queued for reprocessing"
}
```

---

### Dashboard

---

### `GET /api/dashboard/stats`

**Description:** Get aggregated document and chunk statistics with facet breakdowns.

**Auth required:** No

**Success Response (200):**
```json
{
  "total_documents": 500,
  "total_chunks": 12500,
  "total_tokens": 3500000,
  "documents_by_governance": { "Published": 350, "Draft": 100, "Under Review": 50 },
  "documents_by_sync_status": { "synced": 490, "sync_failed": 10 },
  "documents_by_index_status": { "indexed": 480, "not_indexed": 20 },
  "documents_by_jurisdiction": { "federal": 200, "state": 250, "local": 50 },
  "chunks_by_jurisdiction": { "federal": 5000, "state": 6000, "local": 1500 },
  "chunks_by_tax_year": { "2024": 8000, "2023": 4500 }
}
```

---

### `GET /api/dashboard/rag-health`

**Description:** RAG system health: Solr collection status, indexing coverage, averages.

**Auth required:** No

**Success Response (200):**
```json
{
  "solr_documents_healthy": true,
  "solr_chunks_healthy": true,
  "indexed_documents": 480,
  "indexed_chunks": 12000,
  "avg_chunks_per_document": 25.0,
  "avg_tokens_per_chunk": 280.0,
  "coverage_by_jurisdiction": { "federal": 200, "state": 230, "local": 50 },
  "coverage_by_tax_year": { "2024": 300, "2023": 180 }
}
```

---

### `GET /api/dashboard/alerts`

**Description:** System alerts: Solr outages, review queue size, sync/index failures.

**Auth required:** No

**Success Response (200):**
```json
{
  "alerts": [
    {
      "id": "alert-1",
      "level": "warning",
      "message": "12 documents pending human review",
      "timestamp": "2024-12-01T12:00:00Z",
      "resolved": false
    }
  ],
  "total": 1
}
```

---

### `GET /api/dashboard/freshness`

**Description:** Document freshness metrics: stale document counts, recent URL scraping activity.

**Auth required:** No

**Success Response (200):**
```json
{
  "docs_stale_over_30_days": 15,
  "docs_stale_over_1_year": 3,
  "docs_stale_over_2_years": 1,
  "urls_scraped_last_7_days": 8,
  "stale_documents": [],
  "recent_url_activity": []
}
```

---

### `GET /api/dashboard/scalability`

**Description:** Scale metrics: total resources, job throughput, success rates.

**Auth required:** No

**Success Response (200):**
```json
{
  "total_documents": 500,
  "total_chunks": 12500,
  "total_urls": 25,
  "active_urls": 20,
  "total_jobs_last_24h": 10,
  "documents_processed_last_24h": 35,
  "avg_job_duration_seconds": 120.5,
  "job_success_rate": 0.95,
  "documents_by_status": { "completed": 30, "failed": 5 }
}
```

---

### Governance

---

### `GET /api/governance/logs`

**Description:** Query governance history entries extracted from Solr document `governanceHistory` fields.

**Auth required:** No

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | No | Filter by document ID |
| `from_state` | string | No | Filter by origin state |
| `to_state` | string | No | Filter by target state |
| `changed_by` | string | No | Filter by actor |
| `page` | int | No | Page number (default 1) |
| `limit` | int | No | Items per page (default 20) |

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "log-uuid",
      "document_id": "doc-uuid",
      "document_name": "form-1040.pdf",
      "from_state": "Draft",
      "to_state": "Under Review",
      "changed_by": "admin@example.com",
      "reason": "Ready for review",
      "timestamp": "2024-12-01T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20,
  "pages": 1,
  "has_next": false,
  "has_prev": false
}
```

---

### `POST /api/governance/logs`

**Description:** Apply a governance state change to a document and record it in PostgreSQL audit log.

**Auth required:** No

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | Yes | Target document ID |
| `to_state` | string | Yes | New governance state |
| `changed_by` | string | Yes | Actor performing the change |
| `reason` | string | No | Reason for the transition |

**Success Response (201):** `GovernanceLogEntry` object.

---

### `GET /api/governance/logs/{document_id}`

**Description:** Get all governance history entries for a specific document.

**Auth required:** No

**Success Response (200):** Array of `GovernanceLogEntry` objects.

---

### URL Management

---

### `GET /api/urls`

**Description:** List configured scrape URLs with filtering and pagination.

**Auth required:** No

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `state` | string | No | Filter by state code |
| `status` | string | No | `active`, `inactive`, `error`, `scraping` |
| `data_source` | string | No | `scrape` or `file` |
| `search` | string | No | Free-text search |
| `page` | int | No | Page number (default 1) |
| `limit` | int | No | Items per page (default 20) |

**Success Response (200):** `URLListResponse` -- paginated list of `URLResponse` objects.

---

### `GET /api/urls/{url_id}`

**Description:** Get a single scrape URL by ID.

**Auth required:** No

**Success Response (200):** `URLResponse` object.

| Status | Message |
|---|---|
| 404 | URL not found |

---

### `POST /api/urls`

**Description:** Create a new scrape URL.

**Auth required:** No

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `url` | string | Yes | URL to scrape |
| `name` | string | No | Display name |
| `description` | string | No | Description |
| `jurisdiction` | string | No | `federal` (default), `state`, or `local` |
| `state` | string | Conditional | Required if jurisdiction is `state` or `local` |
| `city` | string | Conditional | Required if jurisdiction is `local` |
| `data_source` | string | No | `scrape` (default) or `file` |
| `delay_between_requests` | int | No | Delay in seconds (default 2) |
| `max_requests_per_minute` | int | No | Rate limit (default 30) |
| `max_files_per_session` | int | No | Max files per session (default 10000) |

**Success Response (201):** `URLResponse` object.

| Status | Message |
|---|---|
| 400 | Duplicate URL |

---

### `PUT /api/urls/{url_id}`

**Description:** Update a scrape URL.

**Auth required:** No

**Request Body:** `URLUpdate` -- all fields optional.

**Success Response (200):** Updated `URLResponse`.

---

### `DELETE /api/urls/{url_id}`

**Description:** Delete a scrape URL.

**Auth required:** No

**Success Response:** `204 No Content`

---

### `POST /api/urls/{url_id}/scrape`

**Description:** Start a Celery-backed scrape job for the URL.

**Auth required:** No

**Success Response (200):**
```json
{
  "url_id": "uuid",
  "job_id": "job-uuid",
  "status": "running",
  "current": 0,
  "total": 0,
  "message": "Scraping started",
  "documents_created": 0,
  "documents_failed": 0,
  "started_at": "2024-12-01T10:00:00Z"
}
```

---

### `GET /api/urls/{url_id}/scrape/progress`

**Description:** Get latest scrape job progress. Marks stale runs as failed.

**Auth required:** No

**Success Response (200):** `ScrapeProgress` object.

---

### `POST /api/urls/{url_id}/scrape/cancel`

**Description:** Cancel a running scrape job via Redis signal and update the database.

**Auth required:** No

**Success Response (200):**
```json
{
  "message": "Scrape job cancelled",
  "url_id": "uuid"
}
```

---

### Page Discovery

---

### `POST /api/urls/{url_id}/discover`

**Description:** Start a background site crawl to discover linked pages.

**Auth required:** No

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `max_depth` | int | No | Maximum crawl depth 1-10 (default 3) |
| `max_pages` | int | No | Maximum pages 1-5000 (default 500) |
| `respect_robots` | bool | No | Honor robots.txt (default true) |
| `delay_seconds` | float | No | Delay between requests 0.1-10.0 (default 1.0) |
| `add_common_blocks` | bool | No | Add common block patterns (default true) |

**Success Response (200):** `DiscoveryStatusResponse` object.

---

### `GET /api/urls/{url_id}/discover/status`

**Description:** Get current crawl/discovery status from in-memory state.

**Auth required:** No

**Success Response (200):** `DiscoveryStatusResponse` object.

---

### `POST /api/urls/{url_id}/discover/pause`

**Description:** Pause a running discovery crawl.

**Auth required:** No

**Success Response (200):** `DiscoveryStatusResponse` object.

| Status | Message |
|---|---|
| 404 | No active discovery |
| 400 | Cannot pause (not running) |

---

### `POST /api/urls/{url_id}/discover/resume`

**Description:** Resume a paused discovery crawl.

**Auth required:** No

**Success Response (200):** `DiscoveryStatusResponse` object.

---

### `POST /api/urls/{url_id}/discover/cancel`

**Description:** Cancel a running discovery crawl.

**Auth required:** No

**Success Response (200):** `DiscoveryStatusResponse` object.

---

### `GET /api/urls/{url_id}/discovered-pages`

**Description:** List discovered pages with filtering.

**Auth required:** No

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `status` | string | No | `pending`, `approved`, `rejected`, `ingested` |
| `is_document` | bool | No | Filter document-like pages |
| `min_depth` | int | No | Minimum crawl depth |
| `max_depth` | int | No | Maximum crawl depth |
| `page` | int | No | Page number (default 1) |
| `limit` | int | No | Items per page (default 20) |

**Success Response (200):** `DiscoveredPageListResponse` -- paginated list of `DiscoveredPageResponse`.

---

### `POST /api/urls/{url_id}/discovered-pages/approve`

**Description:** Approve specific discovered pages by ID.

**Auth required:** No

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `page_ids` | string[] | Yes | List of page IDs to approve |

**Success Response (200):**
```json
{
  "affected_count": 5,
  "message": "5 pages approved"
}
```

---

### `POST /api/urls/{url_id}/discovered-pages/reject`

**Description:** Reject specific discovered pages by ID.

**Auth required:** No

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `page_ids` | string[] | Yes | List of page IDs to reject |
| `reason` | string | No | Rejection reason |

**Success Response (200):** `BulkApprovalResponse` object.

---

### `POST /api/urls/{url_id}/discovered-pages/approve-all`

**Description:** Approve all pending discovered pages for a URL.

**Auth required:** No

**Success Response (200):** `BulkApprovalResponse` object.

---

### `POST /api/urls/{url_id}/discovered-pages/reject-all`

**Description:** Reject all pending discovered pages for a URL.

**Auth required:** No

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `reason` | string | No | Rejection reason |

**Success Response (200):** `BulkApprovalResponse` object.

---

### `GET /api/urls/{url_id}/site-tree`

**Description:** Get a hierarchical tree of all discovered paths for a URL.

**Auth required:** No

**Success Response (200):** Nested `SiteTreeNode` object.

---

### `GET /api/urls/{url_id}/discovery-stats`

**Description:** Get counts of discovered pages grouped by status.

**Auth required:** No

**Success Response (200):**
```json
{
  "total": 250,
  "pending": 100,
  "approved": 80,
  "rejected": 50,
  "ingested": 20,
  "documents": 15
}
```

---

### Path Rules

---

### `GET /api/urls/{url_id}/path-rules`

**Description:** List path include/exclude rules for a URL.

**Auth required:** No

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `rule_type` | string | No | `block` or `allow` |
| `source` | string | No | `manual`, `robots_txt`, or `auto` |
| `page` | int | No | Page number |
| `limit` | int | No | Items per page |

**Success Response (200):** `PathRuleListResponse` object.

---

### `POST /api/urls/{url_id}/path-rules`

**Description:** Create a new path rule for a URL.

**Auth required:** No

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `pattern` | string | Yes | Path pattern (glob or regex) |
| `rule_type` | string | No | `block` (default) or `allow` |
| `reason` | string | No | Why this rule exists |
| `is_regex` | bool | No | Pattern is regex (default false) |
| `is_glob` | bool | No | Pattern is glob (default true) |
| `case_sensitive` | bool | No | Case-sensitive match (default false) |
| `priority` | int | No | Rule priority (default 0) |

**Success Response (201):** `PathRuleResponse` object.

---

### `DELETE /api/urls/{url_id}/path-rules/{rule_id}`

**Description:** Delete a path rule.

**Auth required:** No

**Success Response:** `204 No Content`

| Status | Message |
|---|---|
| 404 | Rule not found |

---

### Audit Logs

---

### `GET /api/audit/logs`

**Description:** Query audit logs with filtering and pagination.

**Auth required:** No

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `action` | string | No | Filter by action (e.g. `update_document`) |
| `resource_type` | string | No | Filter by resource type (e.g. `document`) |
| `resource_id` | string | No | Filter by resource ID |
| `actor` | string | No | Filter by actor |
| `date_from` | datetime | No | Start date filter |
| `date_to` | datetime | No | End date filter |
| `search` | string | No | Free-text search |
| `page` | int | No | Page number (default 1) |
| `limit` | int | No | Items per page (default 20) |

**Success Response (200):** `AuditLogsListResponse` -- paginated list of `AuditLogResponse`.

---

### `GET /api/audit/logs/document/{document_id}`

**Description:** Get all audit log entries for a specific document.

**Auth required:** No

**Success Response (200):** `AuditLogsListResponse`.

---

### `GET /api/audit/logs/governance`

**Description:** Get governance-related audit log entries.

**Auth required:** No

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | No | Filter by document |
| `actor` | string | No | Filter by actor |
| `page` | int | No | Page number |
| `limit` | int | No | Items per page |

**Success Response (200):** `AuditLogsListResponse`.

---

### File Upload

---

### `POST /api/upload`

**Description:** Upload a file (PDF, DOC, DOCX, TXT, XML, HTML) to Azure Blob Storage. The file is registered in PostgreSQL and optionally processed immediately (parsed, chunked, embedded, indexed to Solr) or queued via Celery.

**Auth required:** No

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes | The document file |
| `metadata` | string (JSON) | No | JSON string with `FileUploadMetadata` fields |

**Metadata Fields (`FileUploadMetadata`):**

| Field | Type | Required | Description |
|---|---|---|---|
| `jurisdiction` | string | Yes | `federal`, `state`, or `local` |
| `state` | string | Conditional | Required for `state` or `local` jurisdiction |
| `city` | string | Conditional | Required for `local` jurisdiction |
| `tax_year` | int | No | Tax year (1900-2100) |
| `tax_type` | string | No | Tax type |
| `authority_level` | int | No | Authority level 1-6 |
| `authority_level_rationale` | string | No | Rationale for authority level |
| `knowledge_base_id` | string | No | Knowledge base ID (default `default`) |
| `tags` | string[] | No | Document tags |
| `title` | string | No | Document title |
| `description` | string | No | Description |
| `doc_type` | string | No | Document type |
| `effective_from` | string | No | Effective start date (ISO 8601) |
| `effective_to` | string | No | Effective end date (ISO 8601) |
| `form_family` | string | No | Form family (e.g. `1040`, `SchC`) |

**Success Response (201):**
```json
{
  "document_id": "uuid",
  "registry_id": "uuid",
  "filename": "tax-document.pdf",
  "file_size": 1024000,
  "blob_path": "uploads/uuid.pdf",
  "blob_url": "https://account.blob.core.windows.net/uploads/uuid.pdf",
  "content_type": "application/pdf",
  "status": "indexed",
  "chunks_created": 45,
  "word_count": 12500,
  "page_count": 10,
  "parsing_quality": 0.95,
  "message": "File uploaded and indexed successfully",
  "document": {}
}
```

| Status | Message |
|---|---|
| 400 | Invalid file type or empty file |
| 413 | File exceeds maximum upload size |
| 503 | Azure Blob Storage not configured |

---

### API Push

---

### `POST /api/push`

**Description:** Push or replace a file by external `file_id`. Used for external API integrations to send documents into the system.

**Auth required:** No

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes | The document file |
| `file_id` | string | Yes | External file identifier |
| `metadata` | string (JSON) | No | JSON string with metadata fields |

**Success Response (201):**
```json
{
  "document_id": "uuid",
  "registry_id": "uuid",
  "filename": "document.pdf",
  "file_size": 512000,
  "blob_path": "api-pushed/uuid.pdf",
  "blob_url": "https://...",
  "content_type": "application/pdf",
  "status": "queued",
  "message": "File pushed successfully"
}
```

---

### `GET /api/push/list`

**Description:** List all documents pushed via API (from the registry).

**Auth required:** No

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `page` | int | No | Page number (default 1) |
| `limit` | int | No | Items per page (default 20) |
| `needs_review` | bool | No | Filter by review flag |

**Success Response (200):**
```json
{
  "items": [],
  "page": 1,
  "limit": 20,
  "total": 0
}
```

---

### `DELETE /api/push/{file_id}`

**Description:** Delete a pushed document by its external `file_id`. Removes from Solr, blob storage, and the registry.

**Auth required:** No

**Success Response:** `204 No Content`

| Status | Message |
|---|---|
| 404 | File ID not found |

---

### API Sources

---

### `POST /api/sources`

**Description:** Register an external API source configuration.

**Auth required:** No

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Source name (1-255 chars) |
| `description` | string | No | Description |
| `api_endpoint` | string | Yes | External API URL |
| `category` | string | No | `federal` (default), `state`, `local`, `forms` |
| `auth_type` | string | No | `api_key` (default), `bearer`, `basic`, `oauth`, `none` |
| `api_key` | string | No | API key (stored encrypted) |
| `oauth_token` | string | No | OAuth token (stored encrypted) |
| `custom_headers` | object | No | Custom HTTP headers |
| `fetch_frequency` | string | No | `hourly`, `daily` (default), `weekly`, `monthly` |
| `max_file_size_mb` | int | No | Max file size 1-500 MB (default 50) |

**Success Response (201):** `ApiSourceResponse` object (credentials masked).

---

### `GET /api/sources`

**Description:** List configured API sources with filtering.

**Auth required:** No

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `category` | string | No | Filter by category |
| `status` | string | No | Filter by status |
| `search` | string | No | Free-text search |
| `page` | int | No | Page number |
| `limit` | int | No | Items per page |

**Success Response (200):** `ApiSourceListResponse` -- paginated list.

---

### `GET /api/sources/{source_id}`

**Description:** Get a single API source.

**Auth required:** No

**Success Response (200):** `ApiSourceResponse` object.

| Status | Message |
|---|---|
| 400 | Invalid UUID |
| 404 | Source not found |

---

### `PUT /api/sources/{source_id}`

**Description:** Update an API source configuration.

**Auth required:** No

**Request Body:** `ApiSourceUpdate` -- all fields optional.

**Success Response (200):** Updated `ApiSourceResponse`.

---

### `DELETE /api/sources/{source_id}`

**Description:** Delete an API source.

**Auth required:** No

**Success Response:** `204 No Content`

---

## Database Models

The application uses **PostgreSQL** via **SQLAlchemy 2.0** (async). All models share two common mixins:

- **UUIDMixin**: `id` (UUID primary key, auto-generated)
- **TimestampMixin**: `created_at`, `updated_at` (auto-managed timestamps)

### `document_registry`

Tracks every document in the system regardless of source.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Auto-generated primary key |
| `source_type` | Enum | `upload`, `scrape`, `api` |
| `processing_status` | Enum | `pending`, `queued`, `processing`, `completed`, `failed` |
| `processing_error` | Text | Error message if processing failed |
| `processed_at` | DateTime | When processing completed |
| `solr_document_id` | String(100) | Linked Solr document ID (unique) |
| `scrape_url_id` | UUID (FK) | Link to scrape URL source |
| `scrape_job_id` | UUID (FK) | Link to scrape job |
| `document_name` | String(255) | Original filename |
| `title` | String(500) | Document title |
| `jurisdiction` | String(50) | `federal`, `state`, `local` |
| `state` | String(50) | US state code |
| `city` | String(100) | City name |
| `tax_year` | Integer | Applicable tax year |
| `governance_state` | String(50) | Current governance state |
| `doc_type` | String(100) | Document type |
| `source_url` | Text | Original source URL |
| `version` | Integer | Document version (default 1) |
| `is_latest` | Boolean | Whether this is the latest version |
| `chunk_count` | Integer | Number of chunks in Solr |
| `external_file_id` | String(255) | External file ID for API-pushed docs (unique) |
| `needs_review` | Boolean | Flagged for human review |
| `replaced_at` | DateTime | When this version was replaced |
| `created_at` | DateTime | Record creation time |
| `updated_at` | DateTime | Last update time |

### `document_blobs`

Stores references to files in Azure Blob Storage.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `document_registry_id` | UUID (FK) | Parent document registry entry |
| `blob_type` | String(50) | Blob category |
| `blob_container` | String(100) | Azure container name |
| `blob_path` | Text | Path within container |
| `blob_url` | Text | Full blob URL |
| `original_filename` | String(255) | Original filename |
| `file_size` | Integer | Size in bytes |
| `mime_type` | String(100) | MIME type |
| `content_hash` | String(64) | SHA-256 hash |
| `version` | Integer | Blob version |
| `is_current` | Boolean | Current version flag |
| `created_at` | DateTime | Creation time |

### `scrape_urls`

Configured web scraping sources.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `url` | Text | Target URL (unique) |
| `name` | String(255) | Display name |
| `description` | Text | Description |
| `state` | String(50) | State code |
| `city` | String(100) | City name |
| `jurisdiction` | String(50) | `federal`, `state`, `local` |
| `data_source` | Enum | `scrape` or `file` |
| `delay_between_requests` | Integer | Seconds between requests |
| `max_requests_per_minute` | Integer | Rate limit |
| `max_files_per_session` | Integer | Max files per session |
| `status` | Enum | `active`, `inactive`, `error`, `scraping` |
| `error_message` | Text | Last error |
| `documents_count` | Integer | Total docs scraped |
| `last_scraped_at` | DateTime | Last scrape time |
| `last_successful_at` | DateTime | Last successful scrape |

### `scrape_jobs`

Individual scrape job runs.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `scrape_url_id` | UUID (FK) | Parent URL |
| `status` | Enum | `pending`, `running`, `completed`, `failed`, `cancelled` |
| `progress_current` | Integer | Current progress count |
| `progress_total` | Integer | Total expected |
| `progress_message` | Text | Human-readable progress |
| `documents_created` | Integer | Docs created this run |
| `documents_updated` | Integer | Docs updated this run |
| `documents_failed` | Integer | Docs failed this run |
| `chunks_created` | Integer | Chunks created |
| `started_at` | DateTime | Job start time |
| `completed_at` | DateTime | Job end time |
| `duration_seconds` | Integer | Total duration |
| `error_message` | Text | Error message |
| `error_details` | JSONB | Structured error details |
| `triggered_by` | String(50) | Who/what triggered this job |

### `scrape_job_logs`

Per-job log entries.

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment |
| `job_id` | UUID (FK) | Parent job |
| `level` | Enum | `debug`, `info`, `warning`, `error` |
| `message` | Text | Log message |
| `details` | JSONB | Structured details |
| `created_at` | DateTime | Log timestamp |

### `discovered_pages`

Pages found during site discovery crawls.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `scrape_url_id` | UUID (FK) | Parent URL |
| `url` | Text | Full page URL |
| `path` | Text | URL path component |
| `depth` | Integer | Crawl depth from root |
| `title` | String(500) | Page title |
| `content_type` | String(100) | HTTP content type |
| `status` | Enum | `pending`, `approved`, `rejected`, `ingested` |
| `is_document` | Boolean | Detected as a downloadable document |
| `http_status` | Integer | HTTP status code |
| `parent_page_id` | UUID (FK self) | Parent page in crawl tree |

### `path_rules`

Include/exclude rules for URL scraping.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `scrape_url_id` | UUID (FK) | Parent URL |
| `pattern` | Text | Glob or regex pattern |
| `rule_type` | Enum | `block` or `allow` |
| `is_regex` | Boolean | Pattern is regex |
| `is_glob` | Boolean | Pattern is glob |
| `case_sensitive` | Boolean | Case-sensitive matching |
| `reason` | Text | Why this rule exists |
| `source` | Enum | `manual`, `robots_txt`, `auto` |
| `priority` | Integer | Rule priority |
| `match_count` | Integer | Number of times matched |

### `api_sources`

External API source configurations.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `name` | String(255) | Source name |
| `description` | Text | Description |
| `api_endpoint` | Text | External API URL |
| `category` | Enum | `federal`, `state`, `local`, `forms` |
| `status` | Enum | `active`, `inactive`, `paused` |
| `auth_type` | Enum | `api_key`, `bearer`, `basic`, `oauth`, `none` |
| `api_key_encrypted` | LargeBinary | Encrypted API key |
| `oauth_token_encrypted` | LargeBinary | Encrypted OAuth token |
| `custom_headers` | JSON | Custom HTTP headers |
| `fetch_frequency` | Enum | `hourly`, `daily`, `weekly`, `monthly` |
| `max_file_size_mb` | Integer | Max file size in MB |
| `last_fetched_at` | DateTime | Last fetch time |
| `total_files_pushed` | Integer | Total files received |

### `governance_transitions`

Records of document governance state changes.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `document_registry_id` | UUID (FK) | Parent document |
| `from_state` | String(50) | Previous state |
| `to_state` | String(50) | New state |
| `changed_by` | String(255) | Actor |
| `reason` | Text | Reason for change |
| `created_at` | DateTime | Transition timestamp |

### `audit_logs`

System-wide audit trail.

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment |
| `actor` | String(255) | Who performed the action |
| `action` | String(100) | Action type |
| `resource_type` | String(50) | Resource type (e.g. `document`) |
| `resource_id` | String(100) | Resource ID |
| `resource_name` | String(255) | Resource display name |
| `old_values` | JSONB | Previous values |
| `new_values` | JSONB | New values |
| `details` | Text | Additional details |
| `created_at` | DateTime | Log timestamp |

### `system_settings`

Key-value system configuration store.

| Column | Type | Description |
|---|---|---|
| `key` | String(100) PK | Setting key |
| `value` | JSONB | Setting value |
| `description` | Text | Setting description |
| `updated_at` | DateTime | Last updated |

---

## Authentication & Authorization

The API currently has **no authentication or authorization** on any endpoint. All routes are publicly accessible to any client that can reach the server.

- **No** JWT tokens, API keys, session cookies, or OAuth flows are enforced on incoming requests.
- **CORS middleware** is configured to restrict browser-based cross-origin access to the origins listed in `CORS_ORIGINS`.
- The `ApiSource` model stores credentials (`api_key`, `oauth_token`) for **outbound** calls to external APIs that the system fetches data from -- these are not used to protect inbound API access.
- Solr and Azure Blob Storage credentials are server-side configuration and not exposed to API consumers.

> If you are deploying this to production, you should add an authentication layer (e.g. JWT bearer tokens, API key middleware, or an API gateway).

---

## Error Handling

The API uses FastAPI's standard error response patterns:

### Operational Errors (HTTPException)

Raised explicitly in route handlers. Returns:

```json
{
  "detail": "Human-readable error message"
}
```

Common status codes:

| Status | Meaning |
|---|---|
| 400 | Bad request / business rule violation |
| 404 | Resource not found |
| 413 | Payload too large (file upload) |
| 500 | Internal server error |
| 503 | Service unavailable (e.g. Azure not configured) |

### Validation Errors (Pydantic)

Returned automatically by FastAPI when request body or query parameters fail Pydantic validation:

**Status:** `422 Unprocessable Entity`

```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "String should have at least 1 character",
      "type": "string_too_short"
    }
  ]
}
```

### Health Check

The `/health` endpoint never raises HTTP errors. It returns `200` with a status field:
- `"healthy"` -- all Solr collections are reachable
- `"degraded"` -- some collections unreachable
- `"unhealthy"` -- Solr connection failed entirely (includes `error` field)

---

## Deployment Notes

- The API runs on **Uvicorn** and can be deployed behind any reverse proxy (Nginx, Traefik, etc.).
- **Celery workers** must be started separately for background scraping and document processing tasks.
- **Redis** is required as the Celery message broker and result backend.
- **PostgreSQL** tables are auto-created on startup via `init_db()` in the lifespan handler. Use **Alembic** for production migrations.
- **Azure Blob Storage** is optional for local development but required for file upload/push functionality.
- **Solr** must have `tax_documents` and `tax_chunks` collections created and configured before the API can index documents.
- The application is designed to run at `http://0.0.0.0:8001` by default; override with `API_HOST` and `API_PORT` environment variables.
