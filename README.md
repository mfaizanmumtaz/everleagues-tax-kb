# EverLeagues Tax RAG System - Backend API

A **Retrieval-Augmented Generation (RAG)** knowledge base system for tax documents. This backend ingests, classifies, indexes, and searches tax documents from multiple sources (file uploads, web scraping, and external API feeds). It uses hybrid search combining BM25 lexical matching, vector semantic search, and authority-level weighting to deliver accurate, citation-backed answers to tax-related questions.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **API Framework** | FastAPI (Python 3.12+) |
| **Search Engine** | Apache Solr 9 (BM25 + Dense Vectors) |
| **Relational DB** | PostgreSQL (via SQLAlchemy async + asyncpg) |
| **Blob Storage** | Azure Blob Storage |
| **AI / Embeddings** | OpenAI (`text-embedding-3-small`, `gpt-4o-mini`) |
| **File Parsing** | pdfplumber, PyMuPDF, python-docx, BeautifulSoup |
| **Task Runner** | FastAPI BackgroundTasks |
| **Package Manager** | uv |

---

## Architecture Diagram

```
+-------------------+          +-----------------------------------------+
|                   |   HTTP   |            FastAPI Backend               |
|   Frontend App    +--------->+                                         |
|   (Angular)       |          |  +----------+  +---------------------+  |
|                   |<---------+  | Routers  |  | Background Tasks    |  |
+-------------------+   JSON   |  +----+-----+  | - Scraping          |  |
                               |       |        | - File Processing   |  |
                               |       v        | - Chunking/Embedding|  |
                               |  +----+-----+  +----------+----------+  |
                               |  | Services |             |             |
                               |  +----+-----+             |             |
                               +-------|-------------------|-----------  +
                                       |                   |
                    +------------------+|+------------------+
                    |                   |                   |
              +-----v------+    +------v------+    +-------v--------+
              |  Solr 9     |    | PostgreSQL  |    | Azure Blob     |
              |             |    |             |    | Storage        |
              | tax_documents|   | scrape_urls |    |                |
              | tax_chunks  |    | scrape_jobs |    | raw-documents  |
              | (vectors)   |    | doc_registry|    | uploads        |
              |             |    | audit_logs  |    | api-pushed     |
              +-------------+    +-------------+    +----------------+
                    |
              +-----v------+
              |  OpenAI    |
              |  API       |
              | - Embed    |
              | - LLM      |
              +------------+
```

### Request Flow

```
1. Frontend sends HTTP request to /api/...
2. FastAPI router validates request (Pydantic models)
3. Router calls the appropriate service layer
4. Service interacts with:
   - Solr 9       --> full-text search, vector search, document/chunk CRUD
   - PostgreSQL   --> URL management, job tracking, audit logs, registry
   - Azure Blob   --> file storage (upload, download, delete)
   - OpenAI       --> generate embeddings & LLM answers
5. Response is serialized via Pydantic and returned as JSON
```

---

## Getting Started

### Prerequisites

| Tool | Version |
|---|---|
| Python | >= 3.12 |
| PostgreSQL | >= 14 |
| Apache Solr | 9.x |
| Azure Blob Storage | (or Azurite for local dev) |
| OpenAI API Key | Required for embeddings & LLM |
| uv (package manager) | Latest |

### Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd everleagues-tax-kb

# 2. Install dependencies with uv
uv sync

# 3. Copy and configure environment variables
cp .env.example .env   # or create .env manually (see Environment Variables section)

# 4. Initialize the PostgreSQL database
python init_database.py

# 5. Ensure Solr collections exist
#    Create two collections: tax_documents and tax_chunks
#    (See Solr Configuration section below)

# 6. Run the development server
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Running the Server

```bash
# Option A: Using uvicorn directly
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Option B: Using the main module
uv run python main.py
```

Once running, the API is available at:

| Resource | URL |
|---|---|
| **Base URL** | `http://localhost:8000` |
| **API Prefix** | `http://localhost:8000/api` |
| **Swagger Docs** | `http://localhost:8000/api/docs` |
| **ReDoc** | `http://localhost:8000/api/redoc` |
| **OpenAPI JSON** | `http://localhost:8000/api/openapi.json` |

---

## Project Structure

```
everleagues-tax-kb/
|-- main.py                        # FastAPI app entry point, lifespan, CORS, router registration
|-- init_database.py               # Creates all PostgreSQL tables
|-- pyproject.toml                 # Python project config & dependencies
|-- uv.lock                       # Dependency lock file
|-- .env                           # Environment variables (not committed)
|
|-- app/
    |-- __init__.py
    |-- dependencies.py            # FastAPI dependency injection (shared service instances)
    |
    |-- config/
    |   |-- settings.py            # Pydantic BaseSettings - all env vars with defaults
    |   |-- jurisdiction_config.py # US states, cities, tax categories loader
    |   |-- jurisdictions.json     # JSON data: states, cities, doc types, tax types
    |
    |-- database/
    |   |-- base.py                # SQLAlchemy Base, UUIDMixin, TimestampMixin
    |   |-- connection.py          # Async engine, session factory, get_db dependency
    |
    |-- db_models/                 # SQLAlchemy ORM models (PostgreSQL tables)
    |   |-- scrape_url.py          # ScrapeUrl - web scraping source URLs
    |   |-- scrape_job.py          # ScrapeJob, ScrapeJobLog - scraping job tracking
    |   |-- document_registry.py   # DocumentRegistry, DocumentBlob - unified doc tracking
    |   |-- governance.py          # GovernanceTransition - state change history
    |   |-- audit.py               # AuditLog - system action audit trail
    |   |-- discovered_page.py     # DiscoveredPage - pre-ingestion page review
    |   |-- path_rule.py           # PathRule - URL path block/allow rules
    |   |-- api_source.py          # ApiSource - external API source configs
    |   |-- system.py              # SystemSetting - key-value system config
    |
    |-- models/                    # Pydantic models (API request/response schemas)
    |   |-- common.py              # GovernanceState, FilterParams, PaginatedResponse
    |   |-- document.py            # DocumentCreate, DocumentUpdate, DocumentResponse
    |   |-- search.py              # SearchRequest, SearchResponse, RetrievedChunk
    |   |-- upload.py              # FileUploadMetadata, FileUploadResponse
    |   |-- chunk.py               # Chunk-related models
    |
    |-- routers/                   # FastAPI route handlers (controllers)
    |   |-- search.py              # RAG search endpoint
    |   |-- documents.py           # Document CRUD + governance
    |   |-- dashboard.py           # Stats, health, alerts, freshness, scalability
    |   |-- governance.py          # Governance audit logs
    |   |-- urls.py                # URL/scraping source management + scrape triggers
    |   |-- discovery.py           # Page discovery, approval, path rules
    |   |-- audit.py               # Audit log queries
    |   |-- upload.py              # File upload & processing
    |   |-- api_push.py            # External API file push & management
    |   |-- api_sources.py         # API source configuration CRUD
    |
    |-- services/                  # Business logic layer
    |   |-- solr_service.py        # Async Solr HTTP client (httpx)
    |   |-- search_service.py      # Hybrid RAG search (BM25 + vector + authority)
    |   |-- document_service.py    # Document CRUD, chunking, governance
    |   |-- chunk_service.py       # Chunk management
    |   |-- embedding_service.py   # OpenAI embedding generation
    |   |-- llm_service.py         # LLM for classification & answer generation
    |   |-- document_classifier_service.py  # AI document classification
    |   |-- document_registry_service.py    # Registry CRUD operations
    |   |-- blob_storage_service.py         # Azure Blob upload/download/delete
    |   |-- audit_log_service.py            # Audit log writing & querying
    |   |-- scrape_service.py               # Web scraping pipeline
    |   |-- scrape_job_service.py           # Scrape job lifecycle
    |   |-- url_db_service.py               # URL database operations
    |   |-- discovery_service.py            # Website crawler for page discovery
    |   |-- discovered_page_service.py      # Page approval/rejection
    |   |-- path_rule_service.py            # Path rule management
    |   |-- api_source_service.py           # API source CRUD
    |   |-- text_chunker.py                 # Text splitting into chunks
    |   |-- file_parser/
    |       |-- service.py          # Main file parsing orchestrator
    |       |-- loaders.py          # PDF, DOCX, HTML, TXT loaders
    |       |-- result.py           # Parse result model
    |       |-- exceptions.py       # Parser-specific exceptions
    |
    |-- prompts/
    |   |-- __init__.py             # LLM prompt templates
    |
    |-- utils/
        |-- validators.py           # Validation utilities
```

---

## API Documentation

**Base URL:** `http://localhost:8000`
**API Prefix:** `/api` (all endpoints below are prefixed with `/api`)

> Interactive docs are available at `/api/docs` (Swagger UI) and `/api/redoc` (ReDoc).

---

### Health & Status Endpoints

---

#### Root

- **Method:** `GET`
- **URL:** `/`
- **Description:** Returns basic API information and links to documentation.

**Response:**

```json
{
  "name": "Tax Knowledge Base API",
  "version": "1.0.0",
  "docs": "/api/docs",
  "redoc": "/api/redoc",
  "openapi": "/api/openapi.json"
}
```

**Status Codes:**
- `200` - Success

---

#### Health Check

- **Method:** `GET`
- **URL:** `/health`
- **Description:** Checks the health of the system by verifying connectivity to both Solr collections. Returns `healthy`, `degraded`, or `unhealthy`.

**Response (healthy):**

```json
{
  "status": "healthy",
  "solr_documents": true,
  "solr_chunks": true,
  "version": "1.0.0"
}
```

**Response (unhealthy):**

```json
{
  "status": "unhealthy",
  "solr_documents": false,
  "solr_chunks": false,
  "version": "1.0.0",
  "error": "Connection refused"
}
```

**Status Codes:**
- `200` - Always returns 200 (check `status` field for actual health)

---

### Search & RAG Endpoints

---

#### RAG Search

- **Method:** `POST`
- **URL:** `/api/search/rag`
- **Description:** Performs a Retrieval-Augmented Generation search. Combines BM25 lexical search, vector semantic search, and authority-level weighting to find the most relevant tax document chunks, then optionally generates an LLM answer based on the retrieved context.

**Request Body:**

```json
{
  "query": "What is the standard deduction for 2024?",
  "filters": {
    "jurisdiction": "federal",
    "state": null,
    "city": null,
    "tax_year": 2024,
    "category": null,
    "authority_level": null,
    "governance_state": null,
    "doc_type": null,
    "source_domain": null,
    "needs_human_review": null,
    "is_latest_for_tax_year": true
  },
  "search_quality_controls": {
    "retrieval_mode": "hybrid",
    "authority_weight_control": 0.5,
    "semantic_lexical_balance": 0.5,
    "top_k": 10
  },
  "generate_answer": true
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string | Yes | The search query text (min 1 character) |
| `filters` | object | No | Optional filters to narrow results (see FilterParams below) |
| `search_quality_controls` | object | No | Fine-tune search behavior |
| `generate_answer` | boolean | No | Whether to generate an LLM answer (default: `true`) |

**FilterParams fields:**

| Field | Type | Description |
|---|---|---|
| `jurisdiction` | string | `"federal"`, `"state"`, or `"local"` |
| `state` | string | 2-letter US state code (e.g., `"CA"`, `"NY"`) -- required if jurisdiction is `"state"` or `"local"` |
| `city` | string | City name -- required if jurisdiction is `"local"` |
| `tax_year` | integer | Filter by tax year (e.g., `2024`) |
| `category` | string[] | Filter by category |
| `authority_level` | integer | 1-6 (1 = highest authority like IRC, 6 = lowest like blog posts) |
| `governance_state` | string | `"Draft"`, `"Under Review"`, `"Published"`, `"Deprecated"`, `"Archived"` |
| `doc_type` | string | Document type filter |
| `source_domain` | string | Filter by source domain |
| `needs_human_review` | boolean | Filter by review status |
| `is_latest_for_tax_year` | boolean | Only return latest version for a tax year |

**SearchQualityControls fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `retrieval_mode` | string | `"hybrid"` | `"hybrid"`, `"vector"`, or `"bm25"` |
| `authority_weight_control` | float | `0.5` | Weight for authority level (0.0 - 1.0) |
| `semantic_lexical_balance` | float | `0.5` | 0 = pure lexical, 1 = pure semantic |
| `top_k` | integer | `10` | Number of results to return (1 - 100) |

**Success Response (200):**

```json
{
  "query": "What is the standard deduction for 2024?",
  "retrieved_chunks": [
    {
      "id": "chunk-uuid-1",
      "chunk_id": "doc-uuid_chunk_0",
      "document_name": "irs-publication-501.pdf",
      "content": "For 2024, the standard deduction amounts are: $14,600 for single filers...",
      "relevance_score": 0.92,
      "authority_level": 1,
      "priority_rank": 1,
      "is_preferred": true,
      "tax_year": 2024,
      "jurisdiction": "federal",
      "state": null,
      "source_url": "https://www.irs.gov/pub/irs-pdf/p501.pdf",
      "source_domain": "irs.gov",
      "paragraph_number": 3,
      "file_version": null,
      "effective_from": "2024-01-01T00:00:00Z",
      "conflict_resolution_reason": "higher_authority"
    }
  ],
  "source_documents": [
    {
      "id": "doc-uuid-1",
      "title": "IRS Publication 501 - Standard Deduction",
      "category": "Federal",
      "jurisdiction": "federal",
      "url": "https://www.irs.gov/pub/irs-pdf/p501.pdf",
      "excerpt": "For 2024, the standard deduction amounts are...",
      "authority_level": 1,
      "priority_rank": 1,
      "is_preferred": true,
      "tax_year": 2024,
      "state": null,
      "effective_from": "2024-01-01T00:00:00Z",
      "conflict_resolution_reason": "higher_authority",
      "chunks": []
    }
  ],
  "total_chunks": 15,
  "search_time_ms": 245.3,
  "retrieval_mode": "hybrid",
  "generated_answer": "For the 2024 tax year, the standard deduction is $14,600 for single filers and married individuals filing separately, $29,200 for married couples filing jointly, and $21,900 for heads of household. [Source: IRS Publication 501]",
  "score_weights": {
    "alpha": 0.3,
    "beta": 0.5,
    "gamma": 0.4
  }
}
```

**Error Response (500):**

```json
{
  "detail": "Search service error: Solr connection refused"
}
```

**Status Codes:**
- `200` - Search completed successfully
- `422` - Validation error (invalid query or filter parameters)
- `500` - Server error

---

### Document Management Endpoints

---

#### List Documents

- **Method:** `GET`
- **URL:** `/api/documents`
- **Description:** Returns a paginated list of documents with optional filtering and sorting. All filters are optional.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | string | No | `*:*` | Solr search query |
| `jurisdiction` | string | No | - | `"federal"`, `"state"`, or `"local"` |
| `state` | string | No | - | 2-letter state code |
| `city` | string | No | - | City name |
| `tax_year` | integer | No | - | Tax year |
| `category` | string[] | No | - | Filter by category (repeatable) |
| `authority_level` | integer | No | - | 1-6 |
| `governance_state` | string | No | - | Governance state filter |
| `doc_type` | string | No | - | Document type |
| `needs_human_review` | boolean | No | - | Review status filter |
| `page` | integer | No | `1` | Page number (>= 1) |
| `limit` | integer | No | `20` | Items per page (1-100) |
| `sort` | string | No | `"uploadedDate desc"` | Sort field and direction |

**Success Response (200):**

```json
{
  "items": [
    {
      "id": "abc-123-def",
      "name": "irs-publication-501.pdf",
      "title": "IRS Publication 501 - Standard Deduction",
      "description": "Guidance on standard deduction amounts for 2024",
      "source_url": "https://www.irs.gov/pub/irs-pdf/p501.pdf",
      "source_domain": "irs.gov",
      "tags": ["standard-deduction", "federal"],
      "category": "Federal",
      "doc_type": "publication",
      "tax_year": 2024,
      "tax_type": "income",
      "jurisdiction": "federal",
      "state": null,
      "city": null,
      "authority_level": 1,
      "authority_level_rationale": "Official IRS publication",
      "effective_from": "2024-01-01T00:00:00Z",
      "effective_to": null,
      "applies_to_tax_years": [2024],
      "applies_to_jurisdictions": ["federal"],
      "form_family": null,
      "size": "1024000",
      "knowledge_base_id": "default",
      "sync_status": "synced",
      "index_status": "indexed",
      "sync_error": null,
      "index_error": null,
      "governance_state": "Published",
      "chunk_count": 45,
      "tokens_indexed": 12500,
      "embedding_model": "text-embedding-3-small",
      "last_indexed_at": "2024-12-01T10:30:00Z",
      "needs_human_review": false,
      "review_reason": null,
      "reviewed_at": null,
      "reviewed_by": null,
      "parsing_quality": 0.95,
      "classification_confidence": 0.88,
      "version": 1,
      "superseded_by": null,
      "is_latest_for_tax_year": true,
      "has_newer_version": false,
      "uploaded_date": "2024-11-15T08:00:00Z",
      "last_synced": "2024-12-01T10:30:00Z",
      "created_at": "2024-11-15T08:00:00Z",
      "updated_at": "2024-12-01T10:30:00Z",
      "ingestion_history": [],
      "error_history": [],
      "governance_history": []
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

**Status Codes:**
- `200` - Success
- `422` - Invalid filter parameters
- `500` - Server error

---

#### Get Document by ID

- **Method:** `GET`
- **URL:** `/api/documents/{document_id}`
- **Description:** Returns full details for a single document including governance history.

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | Yes | Document ID |

**Success Response (200):** Same shape as a single item in the list response above.

**Error Response (404):**

```json
{
  "detail": "Document not found"
}
```

**Status Codes:**
- `200` - Success
- `404` - Document not found
- `500` - Server error

---

#### Create Document

- **Method:** `POST`
- **URL:** `/api/documents`
- **Description:** Creates a new document in Solr. This registers document metadata; it does not handle file upload (use `/api/upload` for that).

**Request Body:**

```json
{
  "name": "tax-guide-2024.pdf",
  "title": "California Sales Tax Guide 2024",
  "description": "Comprehensive guide to California sales tax rates and rules",
  "source_url": "https://example.com/ca-sales-tax.pdf",
  "source_domain": "example.com",
  "tags": ["sales-tax", "california"],
  "category": "State",
  "doc_type": "guide",
  "tax_year": 2024,
  "tax_type": "sales",
  "jurisdiction": "state",
  "state": "CA",
  "city": null,
  "authority_level": 3,
  "authority_level_rationale": "State tax agency publication",
  "effective_from": "2024-01-01T00:00:00Z",
  "effective_to": null,
  "applies_to_tax_years": [2024, 2025],
  "applies_to_jurisdictions": ["state"],
  "form_family": null,
  "size": "512000",
  "knowledge_base_id": "default"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Document filename |
| `title` | string | No | Document title |
| `description` | string | No | Document description |
| `source_url` | string | No | Source URL |
| `source_domain` | string | No | Source domain |
| `tags` | string[] | No | Tags (default: `[]`) |
| `category` | string | No | Category |
| `doc_type` | string | No | Document type |
| `tax_year` | integer | No | Tax year |
| `tax_type` | string | No | Tax type |
| `jurisdiction` | string | No | `"federal"`, `"state"`, or `"local"` |
| `state` | string | No | 2-letter state code |
| `city` | string | No | City name |
| `authority_level` | integer | No | 1-6 |
| `authority_level_rationale` | string | No | Reason for authority level |
| `effective_from` | datetime | No | When the document takes effect |
| `effective_to` | datetime | No | When the document expires |
| `applies_to_tax_years` | int[] | No | Applicable tax years |
| `applies_to_jurisdictions` | string[] | No | Applicable jurisdictions |
| `form_family` | string | No | Form family (e.g., `"1040"`, `"SchC"`) |
| `size` | string | No | File size |
| `knowledge_base_id` | string | No | Knowledge base ID (default: `"default"`) |

**Success Response (201):** Returns the created `DocumentResponse` object.

**Status Codes:**
- `201` - Created
- `422` - Validation error
- `500` - Server error

---

#### Update Document

- **Method:** `PUT`
- **URL:** `/api/documents/{document_id}`
- **Description:** Updates document metadata. Only provided fields are updated (partial update).

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | Yes | Document ID |

**Request Body:**

```json
{
  "title": "Updated Title",
  "tags": ["updated-tag"],
  "authority_level": 2,
  "governance_state": null
}
```

All fields are optional. Only include fields you want to change.

**Success Response (200):** Returns the updated `DocumentResponse` object.

**Error Response (404):**

```json
{
  "detail": "Document not found"
}
```

**Status Codes:**
- `200` - Updated
- `404` - Document not found
- `422` - Validation error
- `500` - Server error

---

#### Delete Document

- **Method:** `DELETE`
- **URL:** `/api/documents/{document_id}`
- **Description:** Deletes a document and all its chunks from Solr, and removes its entry from the PostgreSQL document registry.

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | Yes | Document ID |

**Success Response:** `204 No Content` (empty body)

**Error Response (404):**

```json
{
  "detail": "Document not found"
}
```

**Status Codes:**
- `204` - Deleted successfully (no body)
- `404` - Document not found
- `500` - Server error

---

#### Get Document Chunks

- **Method:** `GET`
- **URL:** `/api/documents/{document_id}/chunks`
- **Description:** Returns all chunks belonging to a document with pagination.

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | Yes | Document ID |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `page` | integer | No | `1` | Page number |
| `limit` | integer | No | `100` | Items per page (1-1000) |

**Success Response (200):**

```json
{
  "items": [
    {
      "id": "chunk-uuid",
      "documentId": "doc-uuid",
      "content": "The standard deduction for single filers in 2024 is $14,600...",
      "chunkIndex": 0,
      "tokenCount": 256,
      "jurisdiction": "federal",
      "taxYear": 2024
    }
  ],
  "total": 45,
  "page": 1,
  "limit": 100,
  "pages": 1,
  "has_next": false,
  "has_prev": false
}
```

**Status Codes:**
- `200` - Success
- `404` - Document not found
- `500` - Server error

---

#### Update Document Governance State

- **Method:** `PUT`
- **URL:** `/api/documents/{document_id}/governance`
- **Description:** Updates a document's governance state and appends a history entry.

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | Yes | Document ID |

**Request Body:**

```json
{
  "governance_state": "Published",
  "changed_by": "john.doe@company.com",
  "reason": "Reviewed and approved by tax team"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `governance_state` | string | Yes | One of: `"Draft"`, `"Under Review"`, `"Published"`, `"Deprecated"`, `"Archived"` |
| `changed_by` | string | Yes | Identifier of the user making the change |
| `reason` | string | No | Reason for the state change |

**Success Response (200):** Returns the updated `DocumentResponse` with the new governance history entry appended.

**Status Codes:**
- `200` - Updated
- `404` - Document not found
- `500` - Server error

---

### File Upload & Ingestion Endpoints

---

#### Upload File

- **Method:** `POST`
- **URL:** `/api/upload`
- **Description:** Uploads a file (PDF, DOCX, TXT, XML, HTML) and processes it through the full ingestion pipeline: blob storage, text extraction, AI classification, chunking, embedding generation, and Solr indexing. Processing happens in the background after the file is uploaded.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes | The file to upload (max 50MB by default) |
| `metadata` | string (JSON) | No | JSON string containing document metadata |

**Supported file types:** `.pdf`, `.doc`, `.docx`, `.txt`, `.xml`, `.html`, `.htm`

**Metadata JSON structure:**

```json
{
  "jurisdiction": "state",
  "state": "CA",
  "city": null,
  "tax_year": 2024,
  "tax_type": "income",
  "authority_level": 3,
  "authority_level_rationale": "State agency guidance",
  "knowledge_base_id": "default",
  "tags": ["california", "income-tax"],
  "title": "CA Income Tax Guide",
  "description": "Guide for CA income tax filing",
  "doc_type": "guide",
  "effective_from": "2024-01-01T00:00:00Z",
  "effective_to": null,
  "applies_to_tax_years": [2024],
  "applies_to_jurisdictions": ["state"],
  "form_family": null
}
```

**Metadata validation rules:**
- `jurisdiction` is **required** (`"federal"`, `"state"`, or `"local"`)
- If jurisdiction is `"state"` or `"local"`: `state` is **required**
- If jurisdiction is `"local"`: `city` is also **required**
- `state` must be a valid 2-letter US state code
- `tax_year` must be between 1900 and 2100

**cURL example:**

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@/path/to/tax-document.pdf" \
  -F 'metadata={"jurisdiction":"federal","tax_year":2024,"tags":["irs"]}'
```

**JavaScript fetch example:**

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('metadata', JSON.stringify({
  jurisdiction: 'state',
  state: 'CA',
  tax_year: 2024,
  tags: ['california', 'sales-tax']
}));

const response = await fetch('http://localhost:8000/api/upload', {
  method: 'POST',
  body: formData
});
```

**Success Response (201):**

```json
{
  "document_id": "pending",
  "uploaded_file_id": null,
  "registry_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "filename": "tax-document.pdf",
  "file_size": 1024000,
  "blob_path": "uploads/a1b2c3d4.pdf",
  "blob_url": "https://storageaccount.blob.core.windows.net/uploads/a1b2c3d4.pdf",
  "content_type": "application/pdf",
  "status": "processing",
  "chunks_created": 0,
  "word_count": 0,
  "page_count": 0,
  "parsing_quality": 0.0,
  "message": "File uploaded successfully. Processing in background...",
  "document": null
}
```

**Error Responses:**

```json
// 400 - Bad Request
{ "detail": "Unsupported file type: .exe. Supported types: .pdf, .doc, .docx, .txt, .xml, .html, .htm" }

// 400 - Empty file
{ "detail": "File is empty" }

// 413 - File too large
{ "detail": "File exceeds maximum size of 50MB" }

// 503 - Storage not configured
{ "detail": "Azure Blob Storage is not configured" }
```

**Status Codes:**
- `201` - File uploaded, processing started
- `400` - Bad request (invalid file type, empty file, bad metadata JSON)
- `413` - File too large
- `422` - Metadata validation failed
- `503` - Azure Blob Storage not configured
- `500` - Server error

---

### API Push Endpoints

These endpoints are used by an external API download service to push files into the system.

---

#### Push File

- **Method:** `POST`
- **URL:** `/api/push`
- **Description:** Push a file from an external API download service. If a file with the same `file_id` already exists, the old version is replaced and the document is flagged for review.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes | The file to push |
| `file_id` | string | Yes | External file ID from the API download service (used for deduplication) |
| `metadata` | string (JSON) | No | JSON metadata (same format as upload metadata) |

**cURL example:**

```bash
curl -X POST http://localhost:8000/api/push \
  -F "file=@/path/to/document.pdf" \
  -F "file_id=ext-file-001" \
  -F 'metadata={"jurisdiction":"federal","tax_year":2024}'
```

**Success Response (201):**

```json
{
  "document_id": "pending",
  "uploaded_file_id": null,
  "registry_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "filename": "document.pdf",
  "file_size": 512000,
  "blob_path": "api-pushed/a1b2c3d4.pdf",
  "blob_url": "https://storageaccount.blob.core.windows.net/api-pushed/a1b2c3d4.pdf",
  "content_type": "application/pdf",
  "status": "processing",
  "chunks_created": 0,
  "word_count": 0,
  "page_count": 0,
  "parsing_quality": 0.0,
  "message": "File pushed successfully. Processing in background...",
  "document": null
}
```

If replacing an existing file, `status` will be `"replacing"` and `message` will be `"File replaced successfully. Processing in background..."`.

**Status Codes:**
- `201` - File pushed, processing started
- `400` - Bad request
- `413` - File too large
- `503` - Azure Blob Storage not configured
- `500` - Server error

---

#### List Pushed Files

- **Method:** `GET`
- **URL:** `/api/push/list`
- **Description:** Lists all files pushed via the external API download service. Useful for sync operations or identifying files needing review after replacement.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `page` | integer | No | `1` | Page number |
| `limit` | integer | No | `20` | Items per page (1-100) |
| `needs_review` | boolean | No | - | Filter by review status |

**Success Response (200):**

```json
{
  "items": [
    {
      "registry_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "external_file_id": "ext-file-001",
      "document_name": "document.pdf",
      "title": "Federal Tax Guide",
      "processing_status": "completed",
      "solr_document_id": "solr-doc-uuid",
      "needs_review": false,
      "replaced_at": null,
      "created_at": "2024-12-01T10:30:00Z",
      "jurisdiction": "federal",
      "state": null,
      "chunk_count": 32
    }
  ],
  "page": 1,
  "limit": 20,
  "total": 1
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

#### Delete Pushed File

- **Method:** `DELETE`
- **URL:** `/api/push/{file_id}`
- **Description:** Deletes a file that was pushed via the API download service. Removes the document from Solr, blob storage, and the registry.

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `file_id` | string | Yes | External file ID |

**Success Response:** `204 No Content`

**Error Response (404):**

```json
{
  "detail": "File with ID 'ext-file-001' not found"
}
```

**Status Codes:**
- `204` - Deleted
- `404` - File not found
- `500` - Server error

---

### URL Management & Web Scraping Endpoints

---

#### List URLs

- **Method:** `GET`
- **URL:** `/api/urls`
- **Description:** Lists all configured scraping URLs with filters and pagination.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `category` | string | No | - | `"Federal"`, `"State"`, `"Local"` |
| `state` | string | No | - | Filter by state |
| `status` | string | No | - | `"active"`, `"inactive"`, `"error"`, `"scraping"` |
| `data_source` | string | No | - | `"scrape"` or `"file"` |
| `search` | string | No | - | Search in URL text |
| `page` | integer | No | `1` | Page number |
| `limit` | integer | No | `20` | Items per page (1-100) |

**Success Response (200):**

```json
{
  "items": [
    {
      "id": "url-uuid",
      "url": "https://www.irs.gov/forms-pubs",
      "name": "IRS Forms & Publications",
      "category": "Federal",
      "state": null,
      "city": null,
      "data_source": "scrape",
      "schedule_frequency": "monthly",
      "status": "active",
      "last_scraped": "2024-12-01T10:30:00Z",
      "documents_count": 150,
      "error_message": null,
      "delay_between_requests": 2,
      "max_requests_per_minute": 30,
      "max_files_per_session": 10000,
      "created_at": "2024-11-01T08:00:00Z",
      "updated_at": "2024-12-01T10:30:00Z"
    }
  ],
  "total": 10,
  "page": 1,
  "limit": 20,
  "pages": 1,
  "has_next": false,
  "has_prev": false
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

#### Get URL by ID

- **Method:** `GET`
- **URL:** `/api/urls/{url_id}`
- **Description:** Returns a single URL configuration by its ID.

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `url_id` | string | Yes | URL ID (UUID) |

**Success Response (200):** Single `URLResponse` object (same shape as items in list).

**Status Codes:**
- `200` - Success
- `404` - URL not found
- `500` - Server error

---

#### Create URL

- **Method:** `POST`
- **URL:** `/api/urls`
- **Description:** Adds a new URL for scraping. Validates that the URL doesn't already exist.

**Request Body:**

```json
{
  "url": "https://www.irs.gov/forms-pubs",
  "name": "IRS Forms & Publications",
  "description": "Official IRS forms and publications page",
  "category": "Federal",
  "state": null,
  "city": null,
  "data_source": "scrape",
  "schedule_frequency": "monthly",
  "delay_between_requests": 2,
  "max_requests_per_minute": 30,
  "max_files_per_session": 10000
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `url` | string | Yes | - | URL to scrape |
| `name` | string | No | - | Display name |
| `description` | string | No | - | Description |
| `category` | string | No | `"Federal"` | `"Federal"`, `"State"`, or `"Local"` |
| `state` | string | No | - | State code |
| `city` | string | No | - | City name |
| `data_source` | string | No | `"scrape"` | `"scrape"` or `"file"` |
| `schedule_frequency` | string | No | `"on_demand"` | `"on_demand"`, `"daily"`, `"weekly"`, `"monthly"`, `"quarterly"`, `"yearly"` |
| `delay_between_requests` | integer | No | `2` | Seconds between requests (>= 1) |
| `max_requests_per_minute` | integer | No | `30` | Max requests per minute (>= 1) |
| `max_files_per_session` | integer | No | `10000` | Max files to download (>= 1) |

**Success Response (201):** Returns the created `URLResponse` object.

**Error Response (400):**

```json
{
  "detail": "URL already exists"
}
```

**Status Codes:**
- `201` - Created
- `400` - URL already exists
- `422` - Validation error
- `500` - Server error

---

#### Update URL

- **Method:** `PUT`
- **URL:** `/api/urls/{url_id}`
- **Description:** Updates a URL configuration. Only provided fields are updated.

**Request Body:**

```json
{
  "schedule_frequency": "weekly",
  "status": "inactive"
}
```

All fields are optional.

**Status Codes:**
- `200` - Updated
- `404` - URL not found
- `500` - Server error

---

#### Delete URL

- **Method:** `DELETE`
- **URL:** `/api/urls/{url_id}`
- **Description:** Deletes a URL and all associated data (jobs, discovered pages, path rules).

**Status Codes:**
- `204` - Deleted
- `404` - URL not found
- `500` - Server error

---

#### Trigger Scrape

- **Method:** `POST`
- **URL:** `/api/urls/{url_id}/scrape`
- **Description:** Triggers a scraping job for a URL. Downloads all approved discovered pages and processes them through the full ingestion pipeline (blob storage, parse, classify, chunk, embed, Solr index). Runs as a background task.

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `url_id` | string | Yes | URL ID |

**Success Response (200):**

```json
{
  "url_id": "url-uuid",
  "job_id": "job-uuid",
  "status": "pending",
  "current": 0,
  "total": 0,
  "message": "Scrape job created, starting...",
  "documents_created": 0,
  "documents_failed": 0,
  "started_at": null
}
```

If already scraping, returns the current progress instead.

**Status Codes:**
- `200` - Scrape started or already in progress
- `404` - URL not found
- `500` - Server error

---

#### Get Scrape Progress

- **Method:** `GET`
- **URL:** `/api/urls/{url_id}/scrape/progress`
- **Description:** Returns the current scraping progress for a URL. Poll this endpoint to track scraping status.

**Success Response (200):**

```json
{
  "url_id": "url-uuid",
  "job_id": "job-uuid",
  "status": "running",
  "current": 45,
  "total": 150,
  "message": "Processing page 45 of 150",
  "documents_created": 40,
  "documents_failed": 2,
  "started_at": "2024-12-01T10:30:00Z"
}
```

Possible `status` values: `"idle"`, `"pending"`, `"running"`, `"completed"`, `"failed"`, `"cancelled"`.

**Status Codes:**
- `200` - Success
- `404` - URL not found
- `500` - Server error

---

#### Cancel Scrape

- **Method:** `POST`
- **URL:** `/api/urls/{url_id}/scrape/cancel`
- **Description:** Sends a cancellation signal to stop an active scrape job.

**Success Response (200):**

```json
{
  "message": "Cancellation signal sent",
  "url_id": "url-uuid"
}
```

**Status Codes:**
- `200` - Cancellation signal sent (or no active scrape to cancel)
- `500` - Server error

---

### Page Discovery Endpoints

These endpoints manage the discovery phase where a website is crawled to find pages before actual content ingestion.

---

#### Start Discovery

- **Method:** `POST`
- **URL:** `/api/urls/{url_id}/discover`
- **Description:** Starts a website crawl to discover pages. Does not ingest content -- just finds and catalogs pages. Discovered pages can then be reviewed and approved before scraping.

**Request Body:**

```json
{
  "max_depth": 3,
  "max_pages": 500,
  "respect_robots": true,
  "delay_seconds": 1.0,
  "add_common_blocks": true
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `max_depth` | integer | No | `3` | Maximum crawl depth (1-10) |
| `max_pages` | integer | No | `500` | Maximum pages to discover (1-5000) |
| `respect_robots` | boolean | No | `true` | Respect robots.txt |
| `delay_seconds` | float | No | `1.0` | Delay between requests (0.1-10.0) |
| `add_common_blocks` | boolean | No | `true` | Add common block patterns (login, cart, etc.) |

**Success Response (200):**

```json
{
  "url_id": "url-uuid",
  "status": "started",
  "pages_discovered": 0,
  "message": "Discovery started",
  "queue_size": 0,
  "current_depth": 0,
  "recent_urls": [],
  "rules_refreshed_count": 0,
  "urls_skipped_by_rules": 0
}
```

**Status Codes:**
- `200` - Discovery started or already in progress
- `404` - URL not found
- `500` - Server error

---

#### Get Discovery Status

- **Method:** `GET`
- **URL:** `/api/urls/{url_id}/discover/status`
- **Description:** Returns the current live discovery status including progress, queue size, and recently discovered URLs.

**Success Response (200):**

```json
{
  "url_id": "url-uuid",
  "status": "running",
  "pages_discovered": 127,
  "message": "Crawling website...",
  "queue_size": 45,
  "current_depth": 2,
  "recent_urls": [
    { "url": "https://example.com/forms/2024", "depth": 2, "title": "2024 Forms" }
  ],
  "rules_refreshed_count": 3,
  "urls_skipped_by_rules": 15
}
```

Possible `status` values: `"idle"`, `"started"`, `"running"`, `"paused"`, `"completed"`, `"cancelled"`, `"error"`.

**Status Codes:**
- `200` - Success

---

#### Pause Discovery

- **Method:** `POST`
- **URL:** `/api/urls/{url_id}/discover/pause`
- **Description:** Pauses an active discovery crawl. The crawl pauses at the next iteration; all pages discovered so far are preserved.

**Status Codes:**
- `200` - Pause signal sent
- `400` - Cannot pause (not running)
- `404` - No discovery found

---

#### Resume Discovery

- **Method:** `POST`
- **URL:** `/api/urls/{url_id}/discover/resume`
- **Description:** Resumes a paused discovery crawl from where it left off.

**Status Codes:**
- `200` - Resume signal sent
- `400` - Cannot resume (not paused)
- `404` - No discovery found

---

#### Cancel Discovery

- **Method:** `POST`
- **URL:** `/api/urls/{url_id}/discover/cancel`
- **Description:** Cancels an active or paused discovery crawl. All pages discovered so far are committed.

**Status Codes:**
- `200` - Cancel signal sent
- `400` - Cannot cancel (already completed/idle)
- `404` - No discovery found

---

#### List Discovered Pages

- **Method:** `GET`
- **URL:** `/api/urls/{url_id}/discovered-pages`
- **Description:** Lists all pages discovered for a URL with filtering and pagination.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `status` | string | No | - | `"pending"`, `"approved"`, `"rejected"`, `"ingested"` |
| `is_document` | boolean | No | - | Filter for downloadable documents only |
| `min_depth` | integer | No | - | Minimum crawl depth |
| `max_depth` | integer | No | - | Maximum crawl depth |
| `page` | integer | No | `1` | Page number |
| `limit` | integer | No | `50` | Items per page (1-200) |

**Success Response (200):**

```json
{
  "items": [
    {
      "id": "page-uuid",
      "url": "https://example.com/forms/2024/form-1040.pdf",
      "path": "/forms/2024/form-1040.pdf",
      "depth": 2,
      "title": "Form 1040 - 2024",
      "content_type": "application/pdf",
      "status": "pending",
      "is_document": true,
      "http_status": 200,
      "discovered_at": "2024-12-01T10:30:00Z"
    }
  ],
  "total": 127,
  "page": 1,
  "limit": 50,
  "pages": 3
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

#### Approve Pages

- **Method:** `POST`
- **URL:** `/api/urls/{url_id}/discovered-pages/approve`
- **Description:** Approve selected pages for ingestion.

**Request Body:**

```json
{
  "page_ids": ["page-uuid-1", "page-uuid-2", "page-uuid-3"],
  "reason": null
}
```

**Success Response (200):**

```json
{
  "affected_count": 3,
  "message": "Approved 3 pages"
}
```

**Status Codes:**
- `200` - Pages approved
- `500` - Server error

---

#### Reject Pages

- **Method:** `POST`
- **URL:** `/api/urls/{url_id}/discovered-pages/reject`
- **Description:** Reject selected pages (they won't be ingested).

**Request Body:**

```json
{
  "page_ids": ["page-uuid-4"],
  "reason": "Not a tax document"
}
```

**Success Response (200):**

```json
{
  "affected_count": 1,
  "message": "Rejected 1 pages"
}
```

**Status Codes:**
- `200` - Pages rejected
- `500` - Server error

---

#### Approve All Pending Pages

- **Method:** `POST`
- **URL:** `/api/urls/{url_id}/discovered-pages/approve-all`
- **Description:** Approves all pages with `pending` status for this URL.

**Success Response (200):**

```json
{
  "affected_count": 85,
  "message": "Approved 85 pages"
}
```

**Status Codes:**
- `200` - All pending pages approved
- `500` - Server error

---

#### Reject All Pending Pages

- **Method:** `POST`
- **URL:** `/api/urls/{url_id}/discovered-pages/reject-all`
- **Description:** Rejects all pages with `pending` status for this URL.

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `reason` | string | No | Rejection reason |

**Status Codes:**
- `200` - All pending pages rejected
- `500` - Server error

---

#### Get Site Tree

- **Method:** `GET`
- **URL:** `/api/urls/{url_id}/site-tree`
- **Description:** Returns a hierarchical tree structure of all discovered pages, organized by URL path.

**Success Response (200):**

```json
{
  "path": "/",
  "depth": 0,
  "page_count": 127,
  "pages": [],
  "children": [
    {
      "path": "/forms",
      "depth": 1,
      "page_count": 45,
      "pages": [
        { "id": "page-uuid", "url": "https://example.com/forms", "status": "approved" }
      ],
      "children": [
        {
          "path": "/forms/2024",
          "depth": 2,
          "page_count": 20,
          "pages": [],
          "children": []
        }
      ]
    }
  ]
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

#### Get Discovery Stats

- **Method:** `GET`
- **URL:** `/api/urls/{url_id}/discovery-stats`
- **Description:** Returns statistics about discovered pages for a URL (counts by status, depth, content type, etc.).

**Success Response (200):**

```json
{
  "total_pages": 127,
  "by_status": {
    "pending": 42,
    "approved": 70,
    "rejected": 10,
    "ingested": 5
  },
  "by_depth": {
    "0": 1,
    "1": 15,
    "2": 67,
    "3": 44
  },
  "documents_count": 35
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

### Path Rules Endpoints

Path rules control which URL paths are blocked or allowed during discovery and scraping.

---

#### List Path Rules

- **Method:** `GET`
- **URL:** `/api/urls/{url_id}/path-rules`
- **Description:** Lists all path rules configured for a URL.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `rule_type` | string | No | - | `"block"` or `"allow"` |
| `source` | string | No | - | `"manual"`, `"robots_txt"`, or `"auto"` |
| `page` | integer | No | `1` | Page number |
| `limit` | integer | No | `50` | Items per page (1-200) |

**Success Response (200):**

```json
{
  "items": [
    {
      "id": "rule-uuid",
      "pattern": "/login/*",
      "rule_type": "block",
      "reason": "Login pages are not tax documents",
      "is_regex": false,
      "is_glob": true,
      "case_sensitive": false,
      "priority": 0,
      "source": "manual",
      "match_count": 5,
      "created_at": "2024-12-01T10:30:00Z"
    }
  ],
  "total": 12
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

#### Create Path Rule

- **Method:** `POST`
- **URL:** `/api/urls/{url_id}/path-rules`
- **Description:** Creates a new path rule for filtering URLs during discovery/scraping.

**Request Body:**

```json
{
  "pattern": "/login/*",
  "rule_type": "block",
  "reason": "Login pages are not relevant",
  "is_regex": false,
  "is_glob": true,
  "case_sensitive": false,
  "priority": 0
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `pattern` | string | Yes | - | Path pattern (e.g., `/login/*`, `*.pdf`) |
| `rule_type` | string | No | `"block"` | `"block"` or `"allow"` |
| `reason` | string | No | - | Why this rule exists |
| `is_regex` | boolean | No | `false` | Pattern is a regex |
| `is_glob` | boolean | No | `true` | Pattern is a glob |
| `case_sensitive` | boolean | No | `false` | Case-sensitive matching |
| `priority` | integer | No | `0` | Higher priority = evaluated first |

**Success Response (201):** Returns the created `PathRuleResponse`.

**Status Codes:**
- `201` - Created
- `500` - Server error

---

#### Delete Path Rule

- **Method:** `DELETE`
- **URL:** `/api/urls/{url_id}/path-rules/{rule_id}`
- **Description:** Deletes a path rule.

**Status Codes:**
- `204` - Deleted
- `404` - Rule not found
- `500` - Server error

---

### API Source Configuration Endpoints

Manage external API source configurations for automated data feeds.

---

#### Create API Source

- **Method:** `POST`
- **URL:** `/api/sources`
- **Description:** Creates a new external API source configuration. API keys and OAuth tokens are stored encrypted.

**Request Body:**

```json
{
  "name": "IRS EForms API",
  "description": "IRS electronic forms download API",
  "api_endpoint": "https://api.irs.gov/v1/forms",
  "category": "federal",
  "auth_type": "api_key",
  "api_key": "your-api-key-here",
  "oauth_token": null,
  "custom_headers": {
    "X-Custom-Header": "value"
  },
  "fetch_frequency": "daily",
  "max_file_size_mb": 50
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | string | Yes | - | Source name (1-255 chars) |
| `description` | string | No | - | Description |
| `api_endpoint` | string | Yes | - | External API URL |
| `category` | string | No | `"federal"` | `"federal"`, `"state"`, `"local"`, `"forms"` |
| `auth_type` | string | No | `"api_key"` | `"api_key"`, `"bearer"`, `"basic"`, `"oauth"`, `"none"` |
| `api_key` | string | No | - | API key (stored encrypted) |
| `oauth_token` | string | No | - | OAuth token (stored encrypted) |
| `custom_headers` | object | No | - | Custom HTTP headers |
| `fetch_frequency` | string | No | `"daily"` | `"hourly"`, `"daily"`, `"weekly"`, `"monthly"` |
| `max_file_size_mb` | integer | No | `50` | Max file size in MB (1-500) |

**Success Response (201):**

```json
{
  "id": "source-uuid",
  "name": "IRS EForms API",
  "description": "IRS electronic forms download API",
  "api_endpoint": "https://api.irs.gov/v1/forms",
  "category": "federal",
  "status": "active",
  "auth_type": "api_key",
  "api_key_configured": true,
  "oauth_token_configured": false,
  "custom_headers": { "X-Custom-Header": "value" },
  "fetch_frequency": "daily",
  "max_file_size_mb": 50,
  "last_fetched_at": null,
  "total_files_pushed": 0,
  "error_message": null,
  "created_at": "2024-12-01T10:30:00Z",
  "updated_at": "2024-12-01T10:30:00Z"
}
```

Note: API keys and tokens are never returned in responses. Instead, `api_key_configured` and `oauth_token_configured` booleans indicate whether they are set.

**Status Codes:**
- `201` - Created
- `422` - Validation error
- `500` - Server error

---

#### List API Sources

- **Method:** `GET`
- **URL:** `/api/sources`
- **Description:** Lists all configured API sources with filtering and pagination.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `category` | string | No | - | `"federal"`, `"state"`, `"local"`, `"forms"` |
| `status` | string | No | - | `"active"`, `"inactive"`, `"paused"` |
| `search` | string | No | - | Search in name, description, endpoint |
| `page` | integer | No | `1` | Page number |
| `limit` | integer | No | `20` | Items per page (1-100) |

**Success Response (200):**

```json
{
  "items": [
    {
      "id": "source-uuid",
      "name": "IRS EForms API",
      "description": "...",
      "api_endpoint": "https://api.irs.gov/v1/forms",
      "category": "federal",
      "status": "active",
      "auth_type": "api_key",
      "api_key_configured": true,
      "oauth_token_configured": false,
      "custom_headers": null,
      "fetch_frequency": "daily",
      "max_file_size_mb": 50,
      "last_fetched_at": "2024-12-01T10:30:00Z",
      "total_files_pushed": 42,
      "error_message": null,
      "created_at": "2024-11-01T08:00:00Z",
      "updated_at": "2024-12-01T10:30:00Z"
    }
  ],
  "total": 3,
  "page": 1,
  "limit": 20,
  "pages": 1,
  "has_next": false,
  "has_prev": false
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

#### Get API Source

- **Method:** `GET`
- **URL:** `/api/sources/{source_id}`
- **Description:** Returns a single API source configuration (credentials masked).

**Status Codes:**
- `200` - Success
- `400` - Invalid source ID format
- `404` - Source not found

---

#### Update API Source

- **Method:** `PUT`
- **URL:** `/api/sources/{source_id}`
- **Description:** Updates an API source configuration. Only provided fields are updated. Pass an empty string for `api_key` or `oauth_token` to clear them.

**Request Body:**

```json
{
  "status": "paused",
  "fetch_frequency": "weekly"
}
```

**Status Codes:**
- `200` - Updated
- `400` - Invalid source ID format
- `404` - Source not found
- `500` - Server error

---

#### Delete API Source

- **Method:** `DELETE`
- **URL:** `/api/sources/{source_id}`
- **Description:** Permanently deletes an API source configuration.

**Status Codes:**
- `204` - Deleted
- `400` - Invalid source ID format
- `404` - Source not found

---

### Dashboard & Metrics Endpoints

---

#### Dashboard Stats

- **Method:** `GET`
- **URL:** `/api/dashboard/stats`
- **Description:** Returns overall system statistics including document/chunk counts with breakdowns by governance state, jurisdiction, sync status, and tax year.

**Success Response (200):**

```json
{
  "total_documents": 500,
  "total_chunks": 15000,
  "total_tokens": 3500000,
  "documents_by_governance": {
    "Draft": 50,
    "Under Review": 30,
    "Published": 400,
    "Deprecated": 15,
    "Archived": 5
  },
  "documents_by_sync_status": {
    "synced": 490,
    "sync_failed": 10
  },
  "documents_by_index_status": {
    "indexed": 480,
    "not_indexed": 20
  },
  "documents_by_jurisdiction": {
    "federal": 200,
    "state": 250,
    "local": 50
  },
  "chunks_by_jurisdiction": {
    "federal": 6000,
    "state": 7500,
    "local": 1500
  },
  "chunks_by_tax_year": {
    "2024": 8000,
    "2023": 5000,
    "2022": 2000
  }
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

#### RAG Health Metrics

- **Method:** `GET`
- **URL:** `/api/dashboard/rag-health`
- **Description:** Returns RAG system health metrics including Solr collection health, document coverage, and average chunk/token statistics.

**Success Response (200):**

```json
{
  "solr_documents_healthy": true,
  "solr_chunks_healthy": true,
  "indexed_documents": 500,
  "indexed_chunks": 15000,
  "avg_chunks_per_document": 30.0,
  "avg_tokens_per_chunk": 233.33,
  "coverage_by_jurisdiction": {
    "federal": 200,
    "state": 250,
    "local": 50
  },
  "coverage_by_tax_year": {
    "2024": 8000,
    "2023": 5000,
    "2022": 2000
  }
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

#### System Alerts

- **Method:** `GET`
- **URL:** `/api/dashboard/alerts`
- **Description:** Returns a list of active system alerts. Checks for: Solr collection issues, documents needing human review, sync/index failures.

**Success Response (200):**

```json
{
  "alerts": [
    {
      "id": "documents_need_review",
      "level": "warning",
      "message": "12 document(s) need human review",
      "timestamp": "",
      "resolved": false
    },
    {
      "id": "sync_failures",
      "level": "warning",
      "message": "3 document(s) failed to sync",
      "timestamp": "",
      "resolved": false
    }
  ],
  "total": 2
}
```

Alert levels: `"info"`, `"warning"`, `"error"`.

**Status Codes:**
- `200` - Success
- `500` - Server error

---

#### Document Freshness Metrics

- **Method:** `GET`
- **URL:** `/api/dashboard/freshness`
- **Description:** Returns document freshness metrics. Identifies stale documents (not updated in 30+ days, 1+ year, 2+ years) and shows recent URL scraping activity.

**Success Response (200):**

```json
{
  "docs_stale_over_30_days": 45,
  "docs_stale_over_1_year": 20,
  "docs_stale_over_2_years": 5,
  "urls_scraped_last_7_days": 8,
  "stale_documents": [
    {
      "id": "doc-uuid",
      "name": "old-tax-guide.pdf",
      "last_updated": "2023-06-15T10:30:00Z",
      "days_stale": 534,
      "source_url": "https://example.com/old-guide.pdf"
    }
  ],
  "recent_url_activity": [
    {
      "id": "url-uuid",
      "url": "https://www.irs.gov/forms-pubs",
      "last_scraped_at": "2024-12-01T10:30:00Z",
      "status": "active",
      "documents_count": 150
    }
  ]
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

#### Scalability Metrics

- **Method:** `GET`
- **URL:** `/api/dashboard/scalability`
- **Description:** Returns system scalability metrics including document/chunk/URL counts, job statistics from the last 24 hours, and job success rates.

**Success Response (200):**

```json
{
  "total_documents": 500,
  "total_chunks": 15000,
  "total_urls": 25,
  "active_urls": 20,
  "total_jobs_last_24h": 5,
  "documents_processed_last_24h": 30,
  "avg_job_duration_seconds": 120.5,
  "job_success_rate": 95.0,
  "documents_by_status": {
    "indexed": 480,
    "not_indexed": 20
  }
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

### Governance Endpoints

---

#### Get Governance Logs

- **Method:** `GET`
- **URL:** `/api/governance/logs`
- **Description:** Returns paginated governance state change logs across all documents.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `document_id` | string | No | - | Filter by document ID |
| `from_state` | string | No | - | Filter by previous state |
| `to_state` | string | No | - | Filter by new state |
| `changed_by` | string | No | - | Filter by user |
| `page` | integer | No | `1` | Page number |
| `limit` | integer | No | `20` | Items per page (1-100) |

**Success Response (200):**

```json
{
  "items": [
    {
      "id": "doc-uuid_2024-12-01T10:30:00",
      "document_id": "doc-uuid",
      "document_name": "tax-guide-2024.pdf",
      "from_state": "Under Review",
      "to_state": "Published",
      "changed_by": "jane.doe@company.com",
      "reason": "Approved by compliance team",
      "timestamp": "2024-12-01T10:30:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "limit": 20,
  "pages": 2,
  "has_next": true,
  "has_prev": false
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

#### Create Governance Log Entry

- **Method:** `POST`
- **URL:** `/api/governance/logs`
- **Description:** Creates a governance log entry by updating a document's governance state. Also logs the change in the PostgreSQL audit log.

**Request Body:**

```json
{
  "document_id": "doc-uuid",
  "to_state": "Published",
  "changed_by": "jane.doe@company.com",
  "reason": "Reviewed and approved by tax team"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | Yes | Document ID |
| `to_state` | string | Yes | New state: `"Draft"`, `"Under Review"`, `"Published"`, `"Deprecated"`, `"Archived"` |
| `changed_by` | string | Yes | User who made the change |
| `reason` | string | No | Reason for the change |

**Success Response (201):**

```json
{
  "id": "doc-uuid_2024-12-01T10:30:00",
  "document_id": "doc-uuid",
  "document_name": "tax-guide-2024.pdf",
  "from_state": "Under Review",
  "to_state": "Published",
  "changed_by": "jane.doe@company.com",
  "reason": "Reviewed and approved by tax team",
  "timestamp": "2024-12-01T10:30:00Z"
}
```

**Status Codes:**
- `201` - Created
- `404` - Document not found
- `422` - Validation error
- `500` - Server error

---

#### Get Document Governance History

- **Method:** `GET`
- **URL:** `/api/governance/logs/{document_id}`
- **Description:** Returns all governance history entries for a specific document, sorted by timestamp descending.

**Success Response (200):**

```json
[
  {
    "id": "doc-uuid_2024-12-01T10:30:00",
    "document_id": "doc-uuid",
    "document_name": "tax-guide-2024.pdf",
    "from_state": "Under Review",
    "to_state": "Published",
    "changed_by": "jane.doe@company.com",
    "reason": "Approved",
    "timestamp": "2024-12-01T10:30:00Z"
  },
  {
    "id": "doc-uuid_2024-11-15T08:00:00",
    "document_id": "doc-uuid",
    "document_name": "tax-guide-2024.pdf",
    "from_state": "Draft",
    "to_state": "Under Review",
    "changed_by": "john.doe@company.com",
    "reason": "Ready for review",
    "timestamp": "2024-11-15T08:00:00Z"
  }
]
```

**Status Codes:**
- `200` - Success
- `404` - Document not found
- `500` - Server error

---

### Audit Log Endpoints

---

#### List Audit Logs

- **Method:** `GET`
- **URL:** `/api/audit/logs`
- **Description:** Lists all audit log entries with filtering and pagination.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `action` | string | No | - | Filter by action (e.g., `"document.create"`, `"governance.change"`) |
| `resource_type` | string | No | - | Filter by resource type (`"document"`, `"url"`, etc.) |
| `resource_id` | string | No | - | Filter by resource ID |
| `actor` | string | No | - | Filter by actor |
| `date_from` | datetime | No | - | Filter from date (ISO 8601) |
| `date_to` | datetime | No | - | Filter to date (ISO 8601) |
| `search` | string | No | - | Search in details text |
| `page` | integer | No | `1` | Page number |
| `limit` | integer | No | `20` | Items per page (1-100) |

**Success Response (200):**

```json
{
  "items": [
    {
      "id": "123",
      "action": "document.upload",
      "resource_type": "document",
      "resource_id": "doc-uuid",
      "resource_name": "tax-guide-2024.pdf",
      "actor": "api",
      "old_values": null,
      "new_values": {
        "filename": "tax-guide-2024.pdf",
        "file_size": 1024000,
        "chunks_created": 45
      },
      "details": "File processed in background. Chunks: 45",
      "created_at": "2024-12-01T10:30:00Z"
    }
  ],
  "total": 500,
  "page": 1,
  "limit": 20,
  "pages": 25,
  "has_next": true,
  "has_prev": false
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

#### Get Audit Logs for Document

- **Method:** `GET`
- **URL:** `/api/audit/logs/document/{document_id}`
- **Description:** Returns all audit log entries for a specific document.

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | Yes | Document ID |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `page` | integer | No | `1` | Page number |
| `limit` | integer | No | `50` | Items per page (1-100) |

**Success Response (200):** Same shape as list audit logs response.

**Status Codes:**
- `200` - Success
- `500` - Server error

---

#### Get Governance Audit Logs

- **Method:** `GET`
- **URL:** `/api/audit/logs/governance`
- **Description:** Returns audit log entries for governance state changes only.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `document_id` | string | No | - | Filter by document ID |
| `actor` | string | No | - | Filter by actor |
| `page` | integer | No | `1` | Page number |
| `limit` | integer | No | `20` | Items per page (1-100) |

**Success Response (200):** Same shape as list audit logs response.

**Status Codes:**
- `200` - Success
- `500` - Server error

---

## Database Schema

All tables use PostgreSQL. UUIDs are used as primary keys (except auto-increment tables noted below). Timestamps use `TIMESTAMPTZ`.

---

### `scrape_urls`

Stores web scraping source URL configurations.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `url` | TEXT | No | URL to scrape (unique) |
| `name` | VARCHAR(255) | Yes | Display name |
| `description` | TEXT | Yes | Description |
| `category` | VARCHAR(50) | No | Federal / State / Local |
| `state` | VARCHAR(50) | Yes | State name |
| `city` | VARCHAR(100) | Yes | City name |
| `jurisdiction` | VARCHAR(50) | Yes | federal / state / local |
| `data_source` | ENUM | No | `scrape` or `file` |
| `schedule_frequency` | ENUM | No | on_demand / daily / weekly / monthly / quarterly / yearly |
| `next_scheduled_run` | TIMESTAMPTZ | Yes | Next scheduled scrape time |
| `delay_between_requests` | INTEGER | Yes | Seconds between requests (default: 2) |
| `max_requests_per_minute` | INTEGER | Yes | Max RPM (default: 30) |
| `max_files_per_session` | INTEGER | Yes | Max files per session (default: 10000) |
| `status` | ENUM | No | active / inactive / error / scraping |
| `error_message` | TEXT | Yes | Last error message |
| `documents_count` | INTEGER | Yes | Total documents scraped (default: 0) |
| `last_scraped_at` | TIMESTAMPTZ | Yes | Last scrape time |
| `last_successful_at` | TIMESTAMPTZ | Yes | Last successful scrape |
| `created_at` | TIMESTAMPTZ | No | Record creation time |
| `updated_at` | TIMESTAMPTZ | No | Last update time |

**Relationships:** Has many `ScrapeJob`, `DocumentRegistry`, `DiscoveredPage`, `PathRule`

---

### `scrape_jobs`

Tracks individual scraping job executions.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `scrape_url_id` | UUID (FK) | No | References `scrape_urls.id` |
| `status` | ENUM | No | pending / running / completed / failed / cancelled |
| `progress_current` | INTEGER | Yes | Current progress count |
| `progress_total` | INTEGER | Yes | Total items to process |
| `progress_message` | TEXT | Yes | Current progress message |
| `documents_created` | INTEGER | Yes | Documents successfully created |
| `documents_updated` | INTEGER | Yes | Documents updated |
| `documents_failed` | INTEGER | Yes | Documents that failed |
| `chunks_created` | INTEGER | Yes | Chunks created |
| `started_at` | TIMESTAMPTZ | Yes | Job start time |
| `completed_at` | TIMESTAMPTZ | Yes | Job completion time |
| `duration_seconds` | INTEGER | Yes | Total duration |
| `error_message` | TEXT | Yes | Error message if failed |
| `error_details` | JSONB | Yes | Detailed error info |
| `triggered_by` | VARCHAR(50) | Yes | scheduler / manual / api |
| `raw_content_blob_path` | TEXT | Yes | Blob path for raw content |
| `processed_content_blob_path` | TEXT | Yes | Blob path for processed content |
| `created_at` | TIMESTAMPTZ | Yes | Record creation time |

**Relationships:** Belongs to `ScrapeUrl`, has many `ScrapeJobLog`, `DocumentRegistry`

---

### `scrape_job_logs`

Detailed per-step logs for scrape jobs.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | INTEGER | No | Auto-increment primary key |
| `job_id` | UUID (FK) | No | References `scrape_jobs.id` |
| `level` | ENUM | No | debug / info / warning / error |
| `message` | TEXT | No | Log message |
| `details` | JSONB | Yes | Additional details |
| `created_at` | TIMESTAMPTZ | Yes | Timestamp |

---

### `document_registry`

Unified tracking for all documents regardless of source (upload, scrape, or API).

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `source_type` | ENUM | No | upload / scrape / api |
| `processing_status` | ENUM | No | pending / processing / completed / failed |
| `processing_error` | TEXT | Yes | Error message if processing failed |
| `processed_at` | TIMESTAMPTZ | Yes | When processing completed |
| `solr_document_id` | VARCHAR(100) | Yes | Reference to Solr document (unique) |
| `scrape_url_id` | UUID (FK) | Yes | References `scrape_urls.id` |
| `scrape_job_id` | UUID (FK) | Yes | References `scrape_jobs.id` |
| `document_name` | VARCHAR(255) | Yes | Document filename |
| `title` | VARCHAR(500) | Yes | Document title |
| `jurisdiction` | VARCHAR(50) | Yes | federal / state / local |
| `state` | VARCHAR(50) | Yes | State code |
| `city` | VARCHAR(100) | Yes | City name |
| `tax_year` | INTEGER | Yes | Tax year |
| `governance_state` | VARCHAR(50) | Yes | Current governance state |
| `doc_type` | VARCHAR(100) | Yes | Document type |
| `category` | VARCHAR(100) | Yes | Category |
| `source_url` | TEXT | Yes | Original source URL |
| `version` | INTEGER | Yes | Version number (default: 1) |
| `is_latest` | BOOLEAN | Yes | Is this the latest version |
| `chunk_count` | INTEGER | Yes | Number of chunks (default: 0) |
| `external_file_id` | VARCHAR(255) | Yes | External ID from API push (unique) |
| `needs_review` | BOOLEAN | Yes | Flagged for review (default: false) |
| `replaced_at` | TIMESTAMPTZ | Yes | When file was last replaced |
| `created_at` | TIMESTAMPTZ | No | Record creation time |
| `updated_at` | TIMESTAMPTZ | No | Last update time |

**Relationships:** Belongs to `ScrapeUrl`, `ScrapeJob`. Has many `DocumentBlob`, `GovernanceTransition`

---

### `document_blobs`

Blob storage references for document files.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `document_registry_id` | UUID (FK) | No | References `document_registry.id` |
| `blob_type` | VARCHAR(50) | No | raw / processed / chunk |
| `blob_container` | VARCHAR(100) | No | Azure container name |
| `blob_path` | TEXT | No | Path within container |
| `blob_url` | TEXT | Yes | Full Azure Blob URL |
| `original_filename` | VARCHAR(255) | Yes | Original uploaded filename |
| `file_size` | INTEGER | Yes | File size in bytes |
| `mime_type` | VARCHAR(100) | Yes | MIME type |
| `content_hash` | VARCHAR(64) | Yes | SHA-256 hash for deduplication |
| `version` | INTEGER | Yes | Version (default: 1) |
| `is_current` | BOOLEAN | Yes | Is current version (default: true) |
| `created_at` | TIMESTAMPTZ | Yes | Record creation time |

---

### `governance_transitions`

Tracks governance state changes for documents.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `document_registry_id` | UUID (FK) | No | References `document_registry.id` |
| `from_state` | VARCHAR(50) | Yes | Previous state (null for initial) |
| `to_state` | VARCHAR(50) | No | New state |
| `changed_by` | VARCHAR(255) | Yes | User who made the change |
| `reason` | TEXT | Yes | Reason for change |
| `created_at` | TIMESTAMPTZ | Yes | When the change occurred |

---

### `audit_logs`

System-wide audit trail for all actions.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | INTEGER | No | Auto-increment primary key |
| `actor` | VARCHAR(255) | Yes | Who performed the action |
| `action` | VARCHAR(100) | No | Action type (e.g., `document.create`, `governance.change`) |
| `resource_type` | VARCHAR(50) | No | Resource type (`document`, `url`, etc.) |
| `resource_id` | VARCHAR(100) | Yes | Resource ID |
| `resource_name` | VARCHAR(255) | Yes | Resource display name |
| `old_values` | JSONB | Yes | Previous values |
| `new_values` | JSONB | Yes | New values |
| `details` | TEXT | Yes | Human-readable details |
| `created_at` | TIMESTAMPTZ | Yes | Timestamp |

---

### `discovered_pages`

Pages found during the discovery/crawl phase before ingestion.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `scrape_url_id` | UUID (FK) | No | References `scrape_urls.id` |
| `url` | TEXT | No | Full URL |
| `path` | TEXT | No | Relative path from base URL |
| `depth` | INTEGER | Yes | Crawl depth level (default: 0) |
| `title` | VARCHAR(500) | Yes | Page title |
| `content_type` | VARCHAR(100) | Yes | MIME type |
| `content_length` | INTEGER | Yes | Content size in bytes |
| `status` | ENUM | No | pending / approved / rejected / ingested |
| `reviewed_at` | TIMESTAMPTZ | Yes | When reviewed |
| `reviewed_by` | VARCHAR(100) | Yes | Who reviewed |
| `rejection_reason` | TEXT | Yes | Reason if rejected |
| `discovered_at` | TIMESTAMPTZ | Yes | When discovered |
| `discovery_job_id` | UUID | Yes | Which discovery job found this |
| `http_status` | INTEGER | Yes | HTTP status code |
| `is_document` | BOOLEAN | Yes | Is a downloadable document |
| `parent_page_id` | UUID (FK) | Yes | Self-referencing parent page |
| `created_at` | TIMESTAMPTZ | No | Record creation time |
| `updated_at` | TIMESTAMPTZ | No | Last update time |

---

### `path_rules`

URL path patterns for blocking or allowing during discovery/scraping.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `scrape_url_id` | UUID (FK) | No | References `scrape_urls.id` |
| `pattern` | TEXT | No | Path pattern (e.g., `/login/*`) |
| `rule_type` | ENUM | No | block / allow |
| `is_regex` | BOOLEAN | Yes | Pattern is regex (default: false) |
| `is_glob` | BOOLEAN | Yes | Pattern is glob (default: true) |
| `case_sensitive` | BOOLEAN | Yes | Case-sensitive (default: false) |
| `reason` | TEXT | Yes | Why this rule exists |
| `source` | ENUM | No | manual / robots_txt / auto |
| `priority` | INTEGER | Yes | Higher = evaluated first (default: 0) |
| `match_count` | INTEGER | Yes | Times this rule matched (default: 0) |
| `created_at` | TIMESTAMPTZ | No | Record creation time |
| `updated_at` | TIMESTAMPTZ | No | Last update time |

---

### `api_sources`

External API source configurations for automated data feeds.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `name` | VARCHAR(255) | No | Source name |
| `description` | TEXT | Yes | Description |
| `api_endpoint` | TEXT | No | External API endpoint URL |
| `category` | ENUM | No | federal / state / local / forms |
| `status` | ENUM | No | active / inactive / paused |
| `auth_type` | ENUM | No | api_key / bearer / basic / oauth / none |
| `api_key_encrypted` | BYTEA | Yes | Encrypted API key |
| `oauth_token_encrypted` | BYTEA | Yes | Encrypted OAuth token |
| `custom_headers` | JSON | Yes | Custom HTTP headers |
| `fetch_frequency` | ENUM | No | hourly / daily / weekly / monthly |
| `max_file_size_mb` | INTEGER | Yes | Max file size in MB (default: 50) |
| `last_fetched_at` | TIMESTAMPTZ | Yes | Last fetch time |
| `total_files_pushed` | INTEGER | Yes | Total files pushed (default: 0) |
| `error_message` | TEXT | Yes | Last error message |
| `created_at` | TIMESTAMPTZ | No | Record creation time |
| `updated_at` | TIMESTAMPTZ | No | Last update time |

---

### `system_settings`

Key-value store for system-wide configuration.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `key` | VARCHAR(100) | No | Setting key (primary key) |
| `value` | JSONB | No | Setting value |
| `description` | TEXT | Yes | Setting description |
| `updated_at` | TIMESTAMPTZ | Yes | Last update time |

---

### Entity Relationship Diagram

```
scrape_urls
  |-- 1:N --> scrape_jobs
  |             |-- 1:N --> scrape_job_logs
  |             |-- 1:N --> document_registry
  |
  |-- 1:N --> document_registry
  |             |-- 1:N --> document_blobs
  |             |-- 1:N --> governance_transitions
  |
  |-- 1:N --> discovered_pages (self-referencing via parent_page_id)
  |
  |-- 1:N --> path_rules

api_sources (standalone)
audit_logs (standalone)
system_settings (standalone)
```

---

## Solr Configuration

### Collections

| Collection | Purpose |
|---|---|
| `tax_documents` | Document-level metadata, governance state, and faceting |
| `tax_chunks` | Chunk-level data with dense vectors for RAG search |

### Key Fields in `tax_documents`

| Field | Description |
|---|---|
| `id` | Unique document ID |
| `name` | Document filename |
| `title` | Document title |
| `description` | Document description |
| `sourceUrl` | Original source URL |
| `sourceDomain` | Source domain |
| `tags` | Multivalued tags |
| `category` | Document category |
| `docType` | Document type |
| `jurisdiction` | federal / state / local |
| `state` | State code |
| `city` | City name |
| `taxYear` | Tax year |
| `taxType` | Tax type |
| `authorityLevel` | Authority level (1-6) |
| `governanceState` | Draft / Under Review / Published / Deprecated / Archived |
| `syncStatus` | synced / syncing / sync_failed |
| `indexStatus` | indexed / indexing / index_failed / not_indexed |
| `needsHumanReview` | Boolean review flag |
| `chunkCount` | Number of chunks |
| `tokensIndexed` | Total tokens |
| `uploadedDate` | Upload timestamp |
| `updatedAt` | Last update |
| `governanceHistory` | JSON array of governance state changes |
| `ingestionHistory` | JSON array of ingestion events |

### Key Fields in `tax_chunks`

| Field | Description |
|---|---|
| `id` | Unique chunk ID |
| `documentId` | Parent document ID |
| `content` | Chunk text content |
| `vector` | Dense vector embedding (1536 dimensions, `text-embedding-3-small`) |
| `chunkIndex` | Position within document |
| `tokenCount` | Number of tokens in chunk |
| `jurisdiction` | Inherited from parent document |
| `state` | Inherited from parent |
| `taxYear` | Inherited from parent |
| `authorityLevel` | Inherited from parent |
| `sourceDomain` | Inherited from parent |

### Search Modes

The search service supports three modes:

1. **Hybrid** (default) - Combines BM25 + vector similarity + authority weighting using configurable weights:
   - `alpha` (BM25 weight): default `0.3`
   - `beta` (vector weight): default `0.5`
   - `gamma` (authority weight): default `0.4`

2. **Vector** - Pure dense vector (semantic) search using OpenAI embeddings

3. **BM25** - Pure lexical/keyword search

---

## Environment Variables Reference

| Variable | Description | Required | Default |
|---|---|---|---|
| **PostgreSQL** | | | |
| `DATABASE_URL` | PostgreSQL connection string | No | `postgresql://taxkb_user:password@localhost:5432/tax_kb` |
| `DATABASE_ECHO` | Enable SQL query logging | No | `False` |
| `DATABASE_POOL_SIZE` | Connection pool size | No | `10` |
| `DATABASE_MAX_OVERFLOW` | Max overflow connections | No | `20` |
| **Solr** | | | |
| `SOLR_BASE_URL` | Solr base URL | No | `http://localhost:8983/solr` |
| `SOLR_USERNAME` | Solr authentication username | No | `None` |
| `SOLR_PASSWORD` | Solr authentication password | No | `None` |
| `SOLR_DOCUMENTS_COLLECTION` | Documents collection name | No | `tax_documents` |
| `SOLR_CHUNKS_COLLECTION` | Chunks collection name | No | `tax_chunks` |
| **Azure Blob Storage** | | | |
| `AZURE_STORAGE_CONNECTION_STRING` | Full Azure connection string | No | `None` |
| `AZURE_STORAGE_ACCOUNT_NAME` | Azure storage account name | No | `None` |
| `AZURE_STORAGE_ACCOUNT_KEY` | Azure storage account key | No | `None` |
| `AZURE_CONTAINER_RAW` | Container for raw documents | No | `raw-documents` |
| `AZURE_CONTAINER_PROCESSED` | Container for processed docs | No | `processed-documents` |
| `AZURE_CONTAINER_UPLOADS` | Container for uploaded files | No | `uploads` |
| `AZURE_CONTAINER_API_PUSHED` | Container for API-pushed files | No | `api-pushed` |
| **OpenAI** | | | |
| `OPENAI_API_KEY` | OpenAI API key | Yes | `None` |
| `EMBEDDING_MODEL` | Embedding model name | No | `text-embedding-3-small` |
| `EMBEDDING_DIMENSION` | Embedding vector dimension | No | `1536` |
| **LLM** | | | |
| `CLASSIFIER_LLM_MODEL` | Model for document classification | No | `gpt-4o-mini` |
| `CLASSIFIER_LLM_TEMPERATURE` | Temperature for classification | No | `0.1` |
| `CLASSIFIER_LLM_MAX_TOKENS` | Max tokens for classification | No | `500` |
| `RAG_LLM_MODEL` | Model for RAG answer generation | No | `gpt-4o-mini` |
| `RAG_LLM_TEMPERATURE` | Temperature for RAG answers | No | `0.1` |
| `RAG_LLM_MAX_TOKENS` | Max tokens for RAG answers | No | `1500` |
| **Search Weights** | | | |
| `BM25_WEIGHT` | BM25 lexical search weight (alpha) | No | `0.3` |
| `VECTOR_WEIGHT` | Vector semantic search weight (beta) | No | `0.5` |
| `AUTHORITY_WEIGHT` | Authority level weight (gamma) | No | `0.4` |
| **API Server** | | | |
| `API_HOST` | API host address | No | `0.0.0.0` |
| `API_PORT` | API port number | No | `8000` |
| `API_PREFIX` | API route prefix | No | `/api` |
| `DEBUG` | Enable debug mode | No | `False` |
| **CORS** | | | |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | No | `["http://localhost:3000", "http://127.0.0.1:3000"]` |
| `CORS_ALLOW_CREDENTIALS` | Allow credentials | No | `True` |
| `CORS_ALLOW_METHODS` | Allowed HTTP methods (JSON array) | No | `["*"]` |
| `CORS_ALLOW_HEADERS` | Allowed HTTP headers (JSON array) | No | `["*"]` |
| **Pagination** | | | |
| `DEFAULT_PAGE_SIZE` | Default page size for lists | No | `20` |
| `MAX_PAGE_SIZE` | Maximum allowed page size | No | `100` |
| **Scraper** | | | |
| `SCRAPER_DEFAULT_DELAY` | Default delay between requests (seconds) | No | `2.0` |
| `SCRAPER_DEFAULT_RPM` | Default requests per minute | No | `30` |
| `SCRAPER_DEFAULT_TIMEOUT` | Default request timeout (seconds) | No | `30` |
| `SCRAPER_MAX_FILES_PER_SESSION` | Max files per scrape session | No | `10000` |
| **File Upload** | | | |
| `MAX_UPLOAD_SIZE_MB` | Maximum file upload size in MB | No | `50` |
| `ALLOWED_FILE_EXTENSIONS` | Allowed file extensions (JSON array) | No | `[".pdf", ".doc", ".docx", ".txt", ".xml", ".html", ".htm"]` |
| `PROCESS_UPLOADS_SYNC` | Process uploads immediately vs background | No | `True` |

### Example `.env` File

```env
# PostgreSQL
DATABASE_URL=postgresql://taxkb_user:your_password@localhost:5432/tax_kb

# Solr
SOLR_BASE_URL=http://localhost:8983/solr
SOLR_DOCUMENTS_COLLECTION=tax_documents
SOLR_CHUNKS_COLLECTION=tax_chunks

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=youraccountname;AccountKey=youraccountkey;EndpointSuffix=core.windows.net

# OpenAI (REQUIRED)
OPENAI_API_KEY=sk-your-openai-api-key-here

# API Server
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False

# CORS (add your frontend URL)
CORS_ORIGINS=["http://localhost:4200"]
```
