# Frontend Feature Analysis Report for Solr9 Schema Design

**Document Version:** 1.0  
**Date:** 2024-11-20  
**Purpose:** Comprehensive analysis of frontend features to inform Solr9 schema design

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture Overview](#system-architecture-overview)
3. [Module-by-Module Feature Analysis](#module-by-module-feature-analysis)
4. [Data Model Specifications](#data-model-specifications)
5. [Relationship & Correlation Analysis](#relationship--correlation-analysis)
6. [Workflow Documentation](#workflow-documentation)
7. [Solr Schema Design Requirements](#solr-schema-design-requirements)
8. [Implementation Recommendations](#implementation-recommendations)
9. [Appendices](#appendices)

---

## Solr9 Schema Files Created

Based on this analysis, two Solr9 XML schema files have been created:

1. **`backend/solr_schema_tax_documents.xml`** - Document metadata collection (56 fields)
2. **`backend/solr_schema_tax_chunks.xml`** - RAG search collection with 1536-dim vector field (39 fields)

---

## Executive Summary

This report provides a comprehensive analysis of the EverLeagues Tax Knowledge Base frontend application. The system is a sophisticated tax document management and RAG (Retrieval-Augmented Generation) platform with five core modules:

1. **Dashboard Overview** - System metrics, RAG health monitoring, alerting, and freshness tracking
2. **URL Management** - Source URL registration, scheduling, web scraping, and rate limiting
3. **EL Cloud Files** - Document lifecycle management, governance states, authority levels, versioning
4. **Tax Chatbot/Knowledge Base** - RAG-powered search with conflict resolution and document lineage
5. **Governance Audit Log** - Immutable audit trail for compliance (PCAOB, IRS Circular 230, HIPAA)

**Key Findings:**
- System manages documents with 80+ metadata fields per document
- Implements 6-tier authority level system (Level 1 = highest authority)
- Supports complex versioning and supersession chains
- Requires hybrid search (semantic + lexical + authority-weighted)
- Needs comprehensive filtering by jurisdiction, state, category, tax year, authority level
- Requires immutable audit logging for compliance

**Critical Solr Requirements:**
- Vector field for semantic search (KNN)
- Text fields for BM25 keyword search
- Faceting on authority level, jurisdiction, state, category, docType, governanceState
- Range queries on taxYear, dates
- Multi-valued fields for tags, appliesToTaxYears, appliesToJurisdictions
- Nested documents for chunks (or separate collection)

---

## System Architecture Overview

### Technology Stack
- **Frontend Framework:** Next.js 16 with App Router
- **UI Library:** React 19.2.0 with Radix UI components
- **Styling:** Tailwind CSS 4.1.9
- **State Management:** React Context API
- **Form Handling:** React Hook Form with Zod validation
- **Backend Integration:** RESTful API (planned, currently mock data)

### Application Structure

```
frentend/
├── app/
│   ├── page.tsx              # Main page with section routing
│   ├── layout.tsx            # Root layout
│   └── globals.css           # Global styles
├── components/
│   ├── sections/             # Main feature modules
│   │   ├── dashboard-overview.tsx
│   │   ├── url-management.tsx
│   │   ├── el-cloud-files.tsx
│   │   ├── tax-chatbot.tsx
│   │   └── governance-audit-log.tsx
│   ├── dashboard-layout.tsx  # Navigation layout
│   └── ui/                   # Reusable UI components
├── contexts/
│   └── governance-log-context.tsx  # Global governance log state
├── utils/
│   └── governance-logger.ts  # Governance log utilities
└── hooks/                    # Custom React hooks
```

### Data Flow Architecture

```
URL Sources → Scraping → File Ingestion → Parsing → Chunking → 
Embedding → Indexing (Solr) → Governance Review → Publication → 
RAG Search → Results with Citations
```

---

## Module-by-Module Feature Analysis

### 1. Dashboard Overview Module

**File:** `frentend/components/sections/dashboard-overview.tsx`  
**Purpose:** System-wide metrics, RAG health monitoring, operational alerts, and document freshness tracking

#### Features

**1.1 Overview Tab**
- **Primary Metrics:**
  - Documents Processed (count with trend)
  - Active URLs (count with trend)
  - System Uptime (percentage)
  - Processing Speed (time per document)

- **System Scalability Metrics:**
  - Document Processing Capacity (percentage utilization)
  - Storage Utilization (percentage)
  - API Request Quota (percentage)

- **Quick Stats:**
  - Total URLs
  - Last 24h Updates
  - Total Users
  - API Health Status

**1.2 RAG Health Metrics**
- **Primary Metrics:**
  - Documents Indexed (total count)
  - Chunks Created (total count)
  - Embedding Success Rate (percentage)
  - Errors Last 24h (count)

- **Chunk Size Distribution:**
  - Small (< 256 tokens) - percentage
  - Medium (256-512 tokens) - percentage
  - Large (512-1024 tokens) - percentage
  - X-Large (> 1024 tokens) - percentage
  - Average Chunk Size (tokens)

- **Quality Metrics:**
  - Duplicate Detection (count of duplicates prevented)
  - Errors Last 24h (detailed breakdown)

- **Authority Tier Breakdown:**
  - Level 1 (Statute/Reg) - count
  - Level 2 (Forms/Instructions) - count
  - Level 3 (Rulings/Procedures) - count
  - Level 4 (FAQs/Publications) - count
  - Level 5 (Expert Sources) - count
  - Level 6 (Other/Low Authority) - count

**1.3 Operations Tab (Alerts & Issues)**

**Issue Types:**
- `failed_url` - URL download failures
- `corrupted_pdf` - PDF corruption detected
- `timeout` - Request timeouts
- `404_change` - URLs returning 404
- `parsing_failure` - HTML/text parsing failures
- `indexing_failure` - Embedding/indexing failures
- `synced_not_indexed` - Files synced but not indexed

**Issue Severity Levels:**
- `critical` - Requires immediate attention
- `warning` - Should be reviewed
- `info` - Informational

**Issue Data Model:**
```typescript
interface Issue {
  id: string
  type: "failed_url" | "corrupted_pdf" | "timeout" | "404_change" | 
        "parsing_failure" | "indexing_failure" | "synced_not_indexed"
  severity: "critical" | "warning" | "info"
  title: string
  description: string
  url?: string
  fileName?: string
  timestamp: string
  count?: number
}
```

**1.4 Freshness Tab**

**Freshness Metrics:**
- Docs Stale > 30 Days (count)
- Docs Stale > 1 Year (count)
- Docs Stale > 2 Years (count)
- URLs Changed This Week (count)
- New IRS Releases Today (count)
- State Guidance Updated (count)
- FAQ Pages Updated (count)

**Stale Document Data Model:**
```typescript
interface StaleDocument {
  id: string
  name: string
  lastCrawled: string  // ISO date string
  daysStale: number
  sourceUrl: string
  hasNewerVersion: boolean
}
```

**URL Change Data Model:**
```typescript
interface URLChange {
  id: string
  url: string
  changeType: "format_change" | "content_update" | "structure_change" | "version_update"
  description: string
  detectedDate: string  // ISO date string
}
```

**New IRS Release Data Model:**
```typescript
interface NewIRSRelease {
  id: string
  title: string
  releaseDate: string  // ISO date string
  url: string
  type: "form" | "ruling" | "publication" | "other"
}
```

#### Solr Schema Implications

**Required Fields:**
- `lastCrawled` (date) - for freshness queries
- `hasNewerVersion` (boolean) - for stale document detection
- `syncStatus`, `indexStatus` (string) - for issue tracking
- `syncError`, `indexError` (text) - for error details
- `chunkCount` (int) - for RAG metrics
- `tokensIndexed` (int) - for RAG metrics
- `authorityLevel` (int) - for authority tier breakdown
- `embeddingModel` (string) - for RAG health tracking

**Required Queries:**
- Count documents by authority level (facet)
- Count documents by sync/index status (facet)
- Find stale documents (date range query on lastCrawled)
- Find documents with errors (filter on error fields)

---

### 2. URL Management Module

**File:** `frentend/components/sections/url-management.tsx`  
**Purpose:** Manage source URLs for document ingestion, configure scraping schedules, and monitor scraping progress

#### Features

**2.1 URL Data Model**

```typescript
interface URL {
  id: string                    // Unique identifier
  url: string                  // Source URL or file name
  category: "State" | "Federal" // Document category
  state?: string               // US state (if State category)
  active: boolean              // Active/inactive status
  lastUpdated: string          // Last update timestamp (human-readable)
  dataSource: "scrape" | "api" | "file"  // Data source type
  apiKey?: string              // API key (if API source)
  apiEndpoint?: string         // API endpoint (if API source)
  uploadedFile?: File | null   // Uploaded file (if file source)
  fileName?: string            // File name (if file source)
  fileSize?: number            // File size in bytes (if file source)
  scheduleFrequency?: "on_demand" | "daily" | "weekly" | 
                      "monthly" | "quarterly" | "yearly"
  nextScheduledRun?: string    // ISO timestamp
  lastSuccessfulRun?: string    // ISO timestamp
}
```

**2.2 Data Source Types**

1. **Web Scraping (`scrape`)**
   - Scrapes content from URLs
   - Supports rate limiting
   - Progress tracking

2. **API Integration (`api`)**
   - Requires API endpoint and API key
   - Structured data ingestion

3. **File Upload (`file`)**
   - Direct file upload (PDF, DOC, DOCX, TXT, XLSX, XLS)
   - Drag-and-drop support
   - File validation

**2.3 Scheduling System**

**Schedule Frequencies:**
- `on_demand` - Manual execution only
- `daily` - Once per day
- `weekly` - Once per week
- `monthly` - Once per month
- `quarterly` - Once per quarter
- `yearly` - Once per year

**Scheduling Features:**
- "Script Now" option for immediate execution
- Next scheduled run calculation
- Last successful run tracking

**2.4 Rate Limiting Configuration**

**Rate Limit Settings:**
- Delay Between Requests: 1-10 seconds (slider)
- Max Requests Per Minute: 5-60 requests (slider, step 5)
- Max Files Per Session: 100-50,000 files (slider, step 100)

**Rate Limit Purpose:**
- Avoid bot detection
- Prevent overwhelming target servers
- Control system load

**2.5 Scraping Progress Tracking**

**Progress Data Model:**
```typescript
interface ScrapingProgress {
  current: number      // Current progress (0-100)
  total: number        // Total expected (100)
  status: string      // Status message
}
```

**Progress States:**
- Initializing scrape
- Fetching page content
- Parsing HTML
- Extracting documents
- Processing files
- Updating index

**2.6 Duplicate Detection**

- Checks for duplicate URLs before adding
- Highlights duplicates in URL list
- Filter to show only duplicates

#### Solr Schema Implications

**Note:** URLs are likely stored in a separate collection or database, not in Solr document collection. However, URL metadata may be referenced:

**Potential URL-Related Fields in Documents:**
- `sourceUrl` (string) - Link back to URL source
- `sourceDomain` (string) - Extracted domain
- `lastCrawled` (date) - When URL was last crawled
- `dataSource` (string) - How document was ingested

**Required Queries:**
- Find documents by source URL (filter)
- Find documents by source domain (filter)
- Find documents needing re-crawl (date range on lastCrawled)

---

### 3. EL Cloud Files Module

**File:** `frentend/components/sections/el-cloud-files.tsx`  
**Purpose:** Complete document lifecycle management, governance, versioning, and RAG metadata tracking

#### Features

**3.1 Complete File Data Model**

```typescript
interface File {
  // Identity Fields
  id: string
  name: string                    // Display name
  size: string                    // Human-readable size (e.g., "2.4 MB")
  tags: string[]                  // Array of tags
  
  // Temporal Fields
  uploadedDate: string            // ISO date string
  lastCrawled?: string           // ISO timestamp
  effectiveFrom?: string         // ISO date string
  effectiveTo?: string           // ISO date string
  revisionDate?: string          // ISO date string
  
  // Status Fields
  syncStatus: "synced" | "syncing" | "sync_failed"
  indexStatus: "indexed" | "indexing" | "index_failed" | "not_indexed"
  syncError?: string             // Error message if sync failed
  indexError?: string            // Error message if index failed
  
  // Source Tracking
  sourceUrl?: string              // Original source URL
  sourceDomain?: string          // Extracted domain (e.g., "irs.gov")
  knowledgeBaseId?: string        // KB identifier (e.g., "kb_federal_individual")
  knowledgeBaseName?: string      // KB display name
  
  // Tax Year & Jurisdiction
  taxYear?: number               // Primary tax year
  appliesToTaxYears?: number[]   // Array of applicable tax years
  appliesToJurisdictions?: string[]  // Array: ["federal", "state", "CA"]
  
  // Versioning & Supersession
  replacedBy?: string            // Legacy: document name that replaced this
  supersededBy?: string          // Legacy: document name that supersedes this
  supersededByVersionId?: string // Version ID that supersedes (same tax_year only)
  hasNewerVersion?: boolean      // Flag indicating newer version exists
  supersessionChain?: string[]   // Array of document names in chain
  version?: string               // Version identifier (e.g., "2024-v1", "RR-24-01")
  isLatestForTaxYear?: boolean   // Flag: is this latest version for tax year?
  
  // RAG/Indexing Metadata
  chunkCount?: number            // Number of chunks created
  embeddingModel?: string        // Model used (e.g., "text-embedding-3-large")
  tokensIndexed?: number         // Total tokens indexed
  ragErrors?: string             // RAG processing errors
  lastEmbedded?: string          // ISO timestamp of last embedding
  
  // Authority & Classification
  authorityLevel?: 1 | 2 | 3 | 4 | 5 | 6
  authorityLevelRationale?: string  // Explanation of authority assignment
  docType?: "form" | "instructions" | "schedule" | "publication" | "other"
  formFamily?: string            // Form family (e.g., "1040", "SchC", "RR")
  
  // Governance
  governanceState?: "Draft" | "Under Review" | "Published" | "Deprecated"
  
  // Quality & Review
  parsingQuality?: "ok" | "partial" | "failed"
  classificationConfidence?: number  // 0-100 percentage
  needsHumanReview?: boolean        // True if AI confidence < threshold
  reviewReason?: string             // Why flagged for review
  reviewedAt?: string              // ISO timestamp
  reviewedBy?: string              // User ID who reviewed
  
  // History Arrays
  ingestionHistory?: IngestionHistoryEvent[]
  errorHistory?: ErrorHistoryEvent[]
  governanceHistory?: GovernanceHistoryEvent[]
}
```

**3.2 Ingestion History**

```typescript
interface IngestionHistoryEvent {
  timestamp: string              // ISO timestamp
  action: "uploaded" | "synced" | "indexed" | "re_crawled" | "re_indexed"
  status: "success" | "failed" | "in_progress"
  details?: string              // Additional details
  userId?: string               // User who performed action
}
```

**3.3 Error History**

```typescript
interface ErrorHistoryEvent {
  timestamp: string             // ISO timestamp
  type: "sync_error" | "index_error" | "validation_error" | "ocr_error"
  message: string               // Error message
  severity: "critical" | "warning" | "info"
  resolved?: boolean            // Whether error was resolved
  resolvedAt?: string           // ISO timestamp when resolved
}
```

**3.4 Governance History**

```typescript
interface GovernanceHistoryEvent {
  timestamp: string             // ISO timestamp
  action: "state_changed" | "metadata_updated" | "authority_changed"
  userId?: string               // User who performed action
  previousValue?: string        // Previous value
  newValue: string             // New value
  reason?: string              // Reason for change
}
```

**3.5 Authority Level System**

**Level Definitions:**
- **Level 1 - Statute/Reg:** IRC, Treasury Regs, CFR (Highest Authority)
- **Level 2 - Forms/Instructions:** IRS forms
- **Level 3 - Rulings/Procedures:** Revenue Rulings, Notices
- **Level 4 - FAQs/Publications:** IRS FAQs, IRM
- **Level 5 - Expert Sources:** Big-4 memos, CCH, RIA
- **Level 6 - Other/Low Authority:** Blogs, generic articles

**Auto-Assignment Logic (URL Pattern Matching):**
- Level 1: `law.cornell.edu`, `govinfo.gov`, `/irc/`, `/cfr/`, `treasury.gov/regulations`
- Level 2: `irs.gov/forms-pubs`, `irs.gov/forms-instructions`, `/form-`
- Level 3: `irs.gov/pub/irs-drop`, `revenue-ruling`, `revenue-procedure`, `/rr-`, `/rp-`
- Level 4: `irs.gov/faqs`, `irs.gov/publications`, `/pub/`, `/irm/`
- Level 5: `cch.com`, `ria.thomsonreuters.com`, `pwc.com`, `deloitte.com`, `ey.com`, `kpmg.com`
- Level 6: Default (everything else)

**3.6 Governance States**

**State Definitions:**
- **Draft:** Initial state, not yet reviewed
- **Under Review:** Pending human review
- **Published:** Approved and available for use
- **Deprecated:** Superseded or no longer valid

**State Transitions:**
- Auto-assigned "Draft" on ingestion
- Manual promotion to "Under Review"
- Manual promotion to "Published" after verification
- Manual deprecation when superseded

**3.7 Versioning System**

**Version Fields:**
- `version` - Version identifier (e.g., "2024-v1", "RR-24-01")
- `revisionDate` - Date of revision
- `formFamily` - Groups related documents (e.g., "1040", "SchC")
- `isLatestForTaxYear` - Flag indicating latest version for tax year
- `supersededByVersionId` - Links to superseding version (same tax year)

**Supersession Chain:**
- Documents can supersede others within same form family and tax year
- `supersessionChain` array tracks full chain
- Supports both legacy name-based (`supersededBy`) and version-based (`supersededByVersionId`) supersession

**3.8 Tax Year Validity**

**Tax Year Fields:**
- `taxYear` - Primary tax year
- `appliesToTaxYears` - Array of applicable tax years (multi-year documents)
- `effectiveFrom` - Start date of validity
- `effectiveTo` - End date of validity

**3.9 Citability Calculation**

**Citability Criteria:**
1. `governanceState === "Published"`
2. `authorityLevel <= 2` (high authority)
3. `taxYear === currentTaxYear` OR `appliesToTaxYears.includes(currentTaxYear)`
4. `!supersededByVersionId && !supersededBy` (not superseded)
5. `parsingQuality === "ok"` (good parsing quality)

**All criteria must be met for document to be citable.**

**3.10 Classification Confidence System**

**Confidence Threshold:** 70% (below = needs human review)

**Confidence Levels:**
- >= 70%: Green (high confidence)
- 50-69%: Amber (medium confidence, may need review)
- < 50%: Red (low confidence, needs review)

**Review Flags:**
- `needsHumanReview` - Boolean flag
- `reviewReason` - Explanation of why flagged
- `reviewedAt` - Timestamp when reviewed
- `reviewedBy` - User who reviewed

#### Solr Schema Implications

**Critical Fields for Solr:**

**Identity & Content:**
- `id` (string, uniqueKey) - Document ID
- `name` (text) - Document name
- `documentName` (string) - Alternative name field
- `content` (text) - Full text content (for search)
- `excerpt` (text) - Short excerpt/summary
- `title` (text) - Document title

**Source & Metadata:**
- `sourceUrl` (string) - Source URL
- `sourceDomain` (string) - Extracted domain
- `knowledgeBaseId` (string) - KB identifier
- `knowledgeBaseName` (string) - KB display name

**Temporal:**
- `uploadedDate` (date) - Upload date
- `lastCrawled` (date) - Last crawl timestamp
- `effectiveFrom` (date) - Effective start date
- `effectiveTo` (date) - Effective end date
- `revisionDate` (date) - Revision date
- `lastEmbedded` (date) - Last embedding timestamp

**Status:**
- `syncStatus` (string) - Sync status
- `indexStatus` (string) - Index status
- `governanceState` (string) - Governance state
- `parsingQuality` (string) - Parsing quality

**Classification:**
- `authorityLevel` (int) - Authority level (1-6)
- `docType` (string) - Document type
- `formFamily` (string) - Form family
- `category` (string) - Category (forms, instructions, etc.)

**Tax & Jurisdiction:**
- `taxYear` (int) - Primary tax year
- `appliesToTaxYears` (int, multiValued) - Applicable tax years
- `appliesToJurisdictions` (string, multiValued) - Jurisdictions
- `jurisdiction` (string) - Primary jurisdiction
- `state` (string) - State (if applicable)

**Versioning:**
- `version` (string) - Version identifier
- `isLatestForTaxYear` (boolean) - Latest flag
- `supersededByVersionId` (string) - Superseding version ID
- `supersededBy` (string) - Legacy supersession reference
- `hasNewerVersion` (boolean) - Newer version exists

**RAG Metadata:**
- `chunkCount` (int) - Number of chunks
- `tokensIndexed` (int) - Tokens indexed
- `embeddingModel` (string) - Embedding model used
- `ragErrors` (text) - RAG errors
- `vector` (vector, dimension=1536) - Embedding vector (for KNN search)

**Quality:**
- `classificationConfidence` (float) - Confidence score (0-100)
- `needsHumanReview` (boolean) - Review flag

**Tags:**
- `tags` (string, multiValued) - Document tags

**Required Facets:**
- `authorityLevel` (int)
- `docType` (string)
- `jurisdiction` (string)
- `state` (string)
- `category` (string)
- `governanceState` (string)
- `knowledgeBaseId` (string)

**Required Filters:**
- Date range queries on `lastCrawled`, `effectiveFrom`, `effectiveTo`
- Range queries on `taxYear`
- Boolean filters on `isLatestForTaxYear`, `needsHumanReview`
- Multi-value filters on `appliesToTaxYears`, `appliesToJurisdictions`

---

### 4. Tax Chatbot / Knowledge Base Module

**File:** `frentend/components/sections/tax-chatbot.tsx`  
**Purpose:** RAG-powered search interface with intelligent filtering, conflict resolution, and compliance tracking

#### Features

**4.1 Retrieved Chunk Data Model**

```typescript
interface RetrievedChunk {
  id: string                    // Unique chunk ID
  chunkId: string              // Chunk identifier (e.g., "chunk_45")
  documentName: string        // Source document name
  content: string              // Chunk text content
  relevanceScore: number       // Relevance score (0-1)
  authorityLevel?: 1 | 2 | 3 | 4 | 5 | 6
  taxYear?: number
  sourceUrl?: string           // Source document URL
  paragraphNumber?: number     // Paragraph number in document
  fileVersion?: string         // File version
  sourceDomain?: string        // Extracted domain
  effectiveFrom?: string       // Effective date
  jurisdiction?: string        // "federal" | "state" | "local"
  state?: string               // State code (if applicable)
  conflictResolutionReason?: "higher_authority" | "more_recent_date" | 
                             "jurisdiction_match" | null
  priorityRank?: number        // Ranking priority (1 = highest)
  isPreferred?: boolean        // Preferred chunk flag
}
```

**4.2 Source Document Data Model**

```typescript
interface SourceDocument {
  id: string
  title: string                // Document title
  category: string            // Category (forms, instructions, etc.)
  jurisdiction: string        // "federal" | "state" | "local"
  url?: string                // Source URL
  excerpt?: string            // Document excerpt
  authorityLevel?: 1 | 2 | 3 | 4 | 5 | 6
  taxYear?: number
  effectiveFrom?: string
  state?: string
  conflictResolutionReason?: "higher_authority" | "more_recent_date" | 
                             "jurisdiction_match" | null
  priorityRank?: number
  isPreferred?: boolean
  chunks?: RetrievedChunk[]   // Associated chunks
}
```

**4.3 Message Data Model**

```typescript
interface Message {
  id: string
  role: "user" | "assistant"
  content: string             // Message text (with inline citations [1], [2])
  timestamp: Date
  sources?: SourceDocument[]  // Documents used in answer
  retrievedChunks?: RetrievedChunk[]  // Chunks retrieved before answer
}
```

**4.4 Search Quality Controls**

**Retrieval Mode:**
- `balanced` - Balanced approach between precision and recall
- `high_recall` - Prioritize finding all relevant documents
- `high_precision` - Prioritize exact matches

**Authority Weight Control:**
- `strict` - Heavily favor high-authority sources (Level 1-2)
- `balanced` - Moderate authority bias (default)
- `broad` - Minimal authority bias, include lower-authority sources

**Semantic/Lexical Balance:**
- Slider: 0.0 (Lexical) to 1.0 (Semantic)
- 0.0-0.3: More keyword/exact matching
- 0.3-0.7: Balanced
- 0.7-1.0: More semantic/meaning-based matching

**4.5 Filter System**

**Jurisdiction Filter:**
- `federal` - Federal documents
- `state` - State documents
- `local` - Local documents

**State Filter (if jurisdiction = state):**
- NY, CA, NJ, CT, MA, PA (and others)

**City Filter (if jurisdiction = local):**
- NYC, Philadelphia, Los Angeles, Chicago, Houston, Phoenix, etc.

**Category Filter:**
- `forms` - Tax forms
- `instructions` - Form instructions
- `faq` - FAQs
- `code` - Tax code
- `regulations` - Regulations
- `bulletins` - Bulletins
- `sales-tax` - Sales tax

**4.6 Conflict Resolution System**

**Conflict Resolution Reasons:**
- `higher_authority` - Document has higher authority level
- `more_recent_date` - Document has more recent effective date
- `jurisdiction_match` - Document matches query jurisdiction

**Priority Ranking:**
- Priority 1 = Highest priority/preferred
- Priority 2 = Second priority
- Priority 3 = Lower priority
- Chunks sorted by `priorityRank` ascending

**4.7 Document Lineage (Compliance Trace)**

**Lineage Components:**
- Priority Rank
- Source Domain (e.g., "IRS.gov")
- File Name (with version)
- Chunk ID (e.g., "Chunk 45")
- Paragraph Number

**Purpose:**
- Required for PCAOB audits
- Required for IRS Circular 230 compliance
- Required for HIPAA audits
- Legal defensibility
- Conflict resolution audit trail

**4.8 Citation System**

**Inline Citations:**
- Citations appear as `[1]`, `[2]`, etc. in answer text
- Each citation links to a source document
- Citation badges show on hover with document details

**Source Display:**
- "Sources Cited in Response" section
- Shows document title, authority level, tax year
- Links to source URL
- Sorted by priority rank

**4.9 Knowledge Base Statistics**

**Statistics Tracked:**
- Total Documents Indexed
- Total Chunks
- Authority Level Breakdown (by level)
- Sources Distribution (irs.gov, state sites, law.cornell.edu, govinfo.gov)
- Freshness Stats (last 24h, last 7 days, last 30 days, stale > 30 days)

#### Solr Schema Implications

**Critical for RAG Search:**

**Chunk-Level Fields (if chunks stored separately):**
- `chunkId` (string) - Chunk identifier
- `documentId` (string) - Parent document ID
- `content` (text) - Chunk text (for BM25)
- `vector` (vector) - Chunk embedding (for KNN)
- `paragraphNumber` (int) - Paragraph number
- `relevanceScore` (float) - Calculated relevance

**Document-Level Fields (for chunk context):**
- `documentName` (string) - Document name
- `sourceUrl` (string) - Source URL
- `sourceDomain` (string) - Source domain
- `authorityLevel` (int) - Authority level
- `taxYear` (int) - Tax year
- `effectiveFrom` (date) - Effective date
- `jurisdiction` (string) - Jurisdiction
- `state` (string) - State
- `fileVersion` (string) - File version

**Hybrid Search Requirements:**
- Vector field for semantic search (KNN)
- Text field for BM25 keyword search
- Authority level weighting in scoring
- Filter support for jurisdiction, state, category, taxYear

**Conflict Resolution Fields:**
- `priorityRank` (int) - For sorting
- `isPreferred` (boolean) - Preferred flag
- `conflictResolutionReason` (string) - Reason for priority

**Required Query Patterns:**
- KNN vector search with filters
- BM25 text search with filters
- Hybrid scoring: `BM25_score × α + vector_score × β + authority_weight × γ`
- Sorting by priorityRank, relevanceScore
- Faceting on authorityLevel, jurisdiction, category

---

### 5. Governance Audit Log Module

**File:** `frentend/components/sections/governance-audit-log.tsx`  
**Purpose:** Immutable audit trail for all governance actions (compliance requirement)

#### Features

**5.1 Governance Log Entry Data Model**

```typescript
interface GovernanceLogEntry {
  id: string                    // Immutable unique ID (timestamp + random)
  timestamp: string            // ISO 8601 format
  userId: string               // User who performed action
  userEmail?: string           // User email for display
  documentId: string           // Document that was changed
  documentName: string         // Document name for display
  action: "state_changed" | "metadata_updated" | "authority_changed" | 
         "bulk_action" | "document_published" | "document_deprecated"
  fieldChanged: string         // Specific field that changed
  previousValue?: string       // Previous value (stringified)
  newValue: string            // New value (stringified)
  reason?: string             // Reason for change
  ipAddress?: string         // For compliance tracking
  sessionId?: string         // For audit trail
  metadata?: Record<string, unknown>  // Additional context
}
```

**5.2 Action Types**

- `state_changed` - Governance state changed
- `metadata_updated` - Document metadata updated
- `authority_changed` - Authority level changed
- `bulk_action` - Bulk operation performed
- `document_published` - Document published
- `document_deprecated` - Document deprecated

**5.3 Filtering Capabilities**

**Filter Fields:**
- Date range (`dateFrom`, `dateTo`)
- User (`userId`)
- Document (`documentId`, `documentName`)
- Action (`action`)
- Field changed (`fieldChanged`)
- Search query (searches across all text fields)

**5.4 Export Functionality**

- Export to CSV
- Export to JSON
- Includes all log fields

**5.5 Compliance Requirements**

**Required For:**
- Tax audits
- Legal discovery
- Healthcare compliance (HIPAA)
- PCAOB audits
- IRS Circular 230 compliance

**Key Characteristics:**
- Immutable (cannot be edited or deleted)
- Append-only
- Full audit trail
- Timestamped
- User attribution

#### Solr Schema Implications

**Note:** Governance logs may be stored in separate collection or database. However, if stored in Solr:

**Required Fields:**
- `id` (string, uniqueKey) - Log entry ID
- `timestamp` (date) - Action timestamp
- `userId` (string) - User ID
- `userEmail` (string) - User email
- `documentId` (string) - Document ID
- `documentName` (text) - Document name
- `action` (string) - Action type
- `fieldChanged` (string) - Field name
- `previousValue` (text) - Previous value
- `newValue` (text) - New value
- `reason` (text) - Reason for change

**Required Queries:**
- Date range queries on `timestamp`
- Filter by `userId`, `documentId`, `action`, `fieldChanged`
- Full-text search across all fields
- Sorting by timestamp (newest/oldest first)

---

## Data Model Specifications

### Complete Field Reference

#### Document Fields (80+ fields)

**Identity Fields:**
| Field | Type | Required | Multi-Valued | Description |
|-------|------|----------|--------------|-------------|
| `id` | string | Yes | No | Unique document identifier |
| `name` | text | Yes | No | Document display name |
| `documentName` | string | Yes | No | Document file name |
| `title` | text | No | No | Document title |
| `excerpt` | text | No | No | Short excerpt/summary |

**Source Tracking:**
| Field | Type | Required | Multi-Valued | Description |
|-------|------|----------|--------------|-------------|
| `sourceUrl` | string | No | No | Original source URL |
| `sourceDomain` | string | No | No | Extracted domain |
| `knowledgeBaseId` | string | No | No | KB identifier |
| `knowledgeBaseName` | string | No | No | KB display name |

**Temporal Fields:**
| Field | Type | Required | Multi-Valued | Description |
|-------|------|----------|--------------|-------------|
| `uploadedDate` | date | Yes | No | Upload date |
| `lastCrawled` | date | No | No | Last crawl timestamp |
| `effectiveFrom` | date | No | No | Effective start date |
| `effectiveTo` | date | No | No | Effective end date |
| `revisionDate` | date | No | No | Revision date |
| `lastEmbedded` | date | No | No | Last embedding timestamp |

**Status Fields:**
| Field | Type | Required | Multi-Valued | Description |
|-------|------|----------|--------------|-------------|
| `syncStatus` | string | Yes | No | "synced" \| "syncing" \| "sync_failed" |
| `indexStatus` | string | Yes | No | "indexed" \| "indexing" \| "index_failed" \| "not_indexed" |
| `governanceState` | string | No | No | "Draft" \| "Under Review" \| "Published" \| "Deprecated" |
| `syncError` | text | No | No | Sync error message |
| `indexError` | text | No | No | Index error message |

**Classification Fields:**
| Field | Type | Required | Multi-Valued | Description |
|-------|------|----------|--------------|-------------|
| `authorityLevel` | int | No | No | 1-6 (1 = highest) |
| `authorityLevelRationale` | text | No | No | Explanation of authority assignment |
| `docType` | string | No | No | "form" \| "instructions" \| "schedule" \| "publication" \| "other" |
| `formFamily` | string | No | No | Form family (e.g., "1040") |
| `category` | string | No | No | Category type |
| `tags` | string | No | Yes | Array of tags |

**Tax & Jurisdiction:**
| Field | Type | Required | Multi-Valued | Description |
|-------|------|----------|--------------|-------------|
| `taxYear` | int | No | No | Primary tax year |
| `appliesToTaxYears` | int | No | Yes | Applicable tax years |
| `jurisdiction` | string | No | No | "federal" \| "state" \| "local" |
| `state` | string | No | No | US state code |
| `appliesToJurisdictions` | string | No | Yes | Applicable jurisdictions |

**Versioning:**
| Field | Type | Required | Multi-Valued | Description |
|-------|------|----------|--------------|-------------|
| `version` | string | No | No | Version identifier |
| `isLatestForTaxYear` | boolean | No | No | Latest version flag |
| `supersededByVersionId` | string | No | No | Superseding version ID |
| `supersededBy` | string | No | No | Legacy supersession reference |
| `hasNewerVersion` | boolean | No | No | Newer version exists |
| `replacedBy` | string | No | No | Legacy replacement reference |
| `supersessionChain` | string | No | Yes | Array of document names in chain |

**RAG Metadata:**
| Field | Type | Required | Multi-Valued | Description |
|-------|------|----------|--------------|-------------|
| `chunkCount` | int | No | No | Number of chunks |
| `tokensIndexed` | int | No | No | Total tokens indexed |
| `embeddingModel` | string | No | No | Embedding model used |
| `ragErrors` | text | No | No | RAG processing errors |
| `vector` | vector | No | No | Document embedding vector (1536 dim) |

**Quality:**
| Field | Type | Required | Multi-Valued | Description |
|-------|------|----------|--------------|-------------|
| `parsingQuality` | string | No | No | "ok" \| "partial" \| "failed" |
| `classificationConfidence` | float | No | No | Confidence score (0-100) |
| `needsHumanReview` | boolean | No | No | Review flag |
| `reviewReason` | text | No | No | Review reason |
| `reviewedAt` | date | No | No | Review timestamp |
| `reviewedBy` | string | No | No | Reviewer user ID |

**Content:**
| Field | Type | Required | Multi-Valued | Description |
|-------|------|----------|--------------|-------------|
| `content` | text | Yes | No | Full text content |

### Enum Values Reference

**Authority Levels:**
- `1` - Statute/Reg (IRC, Treasury Regs, CFR)
- `2` - Forms/Instructions
- `3` - Rulings/Procedures
- `4` - FAQs/Publications
- `5` - Expert Sources
- `6` - Other/Low Authority

**Governance States:**
- `"Draft"`
- `"Under Review"`
- `"Published"`
- `"Deprecated"`

**Doc Types:**
- `"form"`
- `"instructions"`
- `"schedule"`
- `"publication"`
- `"other"`

**Sync Status:**
- `"synced"`
- `"syncing"`
- `"sync_failed"`

**Index Status:**
- `"indexed"`
- `"indexing"`
- `"index_failed"`
- `"not_indexed"`

**Parsing Quality:**
- `"ok"`
- `"partial"`
- `"failed"`

**Jurisdictions:**
- `"federal"`
- `"state"`
- `"local"`

**Categories:**
- `"forms"`
- `"instructions"`
- `"faq"`
- `"code"`
- `"regulations"`
- `"bulletins"`
- `"sales-tax"`

---

## Relationship & Correlation Analysis

### Entity Relationships

```
URL
  ├──→ File (1:many)          # One URL can produce many files
  │     ├──→ Chunk (1:many)    # One file has many chunks
  │     ├──→ GovernanceLog (1:many)  # One file has many log entries
  │     └──→ File (1:1)        # Supersession relationship
  │
  └──→ Issue (1:many)          # One URL can have many issues

File
  ├──→ Chunk (1:many)          # File contains chunks
  ├──→ GovernanceLog (1:many)  # File has audit log entries
  ├──→ File (supersedes)       # Version chain
  └──→ RetrievedChunk (1:many)  # File chunks retrieved in search

Chunk
  ├──→ File (many:1)           # Chunk belongs to one file
  └──→ RetrievedChunk (1:1)    # Chunk retrieved in search

RetrievedChunk
  ├──→ SourceDocument (many:1) # Multiple chunks from one document
  └──→ Message (many:1)        # Chunks used in message

SourceDocument
  └──→ RetrievedChunk (1:many) # Document has retrieved chunks

Message
  ├──→ SourceDocument (many:many)  # Message cites multiple documents
  └──→ RetrievedChunk (many:many) # Message uses multiple chunks
```

### Data Correlation Matrix

| Entity A | Relationship | Entity B | Cardinality | Key Fields |
|----------|--------------|----------|-------------|------------|
| URL | produces | File | 1:N | `sourceUrl` |
| File | contains | Chunk | 1:N | `id` → `documentId` |
| File | supersedes | File | 1:1 | `supersededByVersionId`, `version` |
| File | generates | GovernanceLog | 1:N | `id` → `documentId` |
| Chunk | belongs_to | File | N:1 | `documentId` → `id` |
| RetrievedChunk | derived_from | Chunk | 1:1 | `chunkId` |
| RetrievedChunk | belongs_to | SourceDocument | N:1 | `documentName` |
| Message | uses | RetrievedChunk | 1:N | `retrievedChunks[]` |
| Message | cites | SourceDocument | 1:N | `sources[]` |

### Version Chain Relationships

**Supersession Chain Logic:**
1. Documents with same `formFamily` and `taxYear` form a version group
2. Within a version group, `version` field determines order
3. `supersededByVersionId` links to superseding version
4. `isLatestForTaxYear` flag indicates latest version
5. `supersessionChain` array tracks full chain

**Example:**
```
Form_1040_2024_v1 (supersededByVersionId: "2024-v2")
  └──→ Form_1040_2024_v2 (supersededByVersionId: "2024-v3")
        └──→ Form_1040_2024_v3 (isLatestForTaxYear: true)
```

---

## Workflow Documentation

### 1. URL to Document Pipeline

**Workflow Steps:**
1. **URL Registration**
   - User adds URL via URL Management interface
   - URL validated
   - Category and state selected (if State)
   - Data source type selected (scrape/api/file)
   - Schedule frequency configured
   - Rate limiting configured

2. **Scheduling**
   - If `scheduleFrequency !== "on_demand"`, calculate `nextScheduledRun`
   - If "Script Now" selected, execute immediately
   - Schedule stored for periodic execution

3. **Scraping Execution**
   - Scraper fetches URL content
   - Progress tracked (`ScrapingProgress`)
   - Rate limiting applied (delay, requests/min, file limit)
   - Files extracted from URL

4. **File Creation**
   - File record created with `syncStatus: "syncing"`
   - `sourceUrl` and `sourceDomain` populated
   - `ingestionHistory` entry added

5. **Processing**
   - File moves to parsing → chunking → embedding → indexing
   - Status updates: `syncStatus: "synced"`, `indexStatus: "indexing"` → `"indexed"`
   - Errors tracked in `errorHistory`

**Error Handling:**
- Sync failures → `syncStatus: "sync_failed"`, `syncError` populated
- Index failures → `indexStatus: "index_failed"`, `indexError` populated
- Retry mechanisms available

### 2. Document Processing Pipeline

**Workflow Steps:**
1. **Sync** (`syncStatus: "syncing"` → `"synced"`)
   - Download/upload file
   - Validate file format
   - Extract metadata

2. **Parse** (`parsingQuality: "ok" | "partial" | "failed"`)
   - Extract text from PDF/HTML
   - Validate text encoding
   - OCR if needed

3. **Chunk** (`chunkCount` populated)
   - Split text into chunks
   - Chunk size: target 256-512 tokens
   - Track chunk count

4. **Embed** (`lastEmbedded` timestamp, `embeddingModel`)
   - Generate embeddings for chunks
   - Store vectors
   - Track embedding model used

5. **Index** (`indexStatus: "indexing"` → `"indexed"`)
   - Index chunks in Solr
   - Index document metadata
   - Track `tokensIndexed`

6. **Review** (`governanceState: "Draft"` → `"Under Review"`)
   - Human review if `needsHumanReview === true`
   - Authority level verification
   - Classification confidence check

7. **Publish** (`governanceState: "Under Review"` → `"Published"`)
   - Document verified
   - Governance log entry created
   - Document available for search

**State Transitions:**
```
Draft → Under Review → Published
  ↓
Deprecated (if superseded)
```

### 3. Search & Retrieval Workflow

**Workflow Steps:**
1. **Query Input**
   - User enters query text
   - Filters selected (jurisdiction, state, city, category)
   - Search quality controls configured

2. **Filter Application**
   - Build filter queries:
     - `jurisdiction:"federal"`
     - `state:"CA"`
     - `category:"forms"`
     - `taxYear:2024`
     - `governanceState:"Published"`
     - `isLatestForTaxYear:true`

3. **Hybrid Search**
   - **Vector Search (KNN):**
     - Generate query embedding
     - KNN search on `vector` field
     - Apply filters
     - Get top K candidates
   
   - **BM25 Search:**
     - Keyword search on `content`, `title`, `excerpt`
     - Apply filters
     - Get top K candidates
   
   - **Hybrid Scoring:**
     - Normalize BM25 and vector scores
     - Calculate authority weight
     - Combine: `BM25_score × α + vector_score × β + authority_weight × γ`
     - Sort by hybrid score

4. **Conflict Resolution**
   - Apply conflict resolution rules:
     - Higher authority → higher priority
     - More recent date → higher priority
     - Jurisdiction match → higher priority
   - Assign `priorityRank` and `isPreferred` flags
   - Sort by `priorityRank`

5. **Result Ranking**
   - Sort by `priorityRank` (ascending)
   - Then by `relevanceScore` (descending)
   - Return top N results

6. **Response Generation**
   - Generate answer with inline citations
   - Create `SourceDocument[]` from chunks
   - Create `RetrievedChunk[]` for lineage
   - Attach to `Message`

7. **Citation & Lineage**
   - Display inline citations `[1]`, `[2]`, etc.
   - Show "Sources Cited" section
   - Show "RAG Retrieval Results" (chunks)
   - Show "Document Lineage" (compliance trace)

### 4. Governance Workflow

**Workflow Steps:**
1. **State Change Request**
   - User initiates state change
   - Selects new state
   - Provides reason (required for deprecation)

2. **Audit Log Creation**
   - Create `GovernanceLogEntry`:
     - `action: "state_changed"`
     - `fieldChanged: "governanceState"`
     - `previousValue`: current state
     - `newValue`: new state
     - `reason`: user-provided reason
     - `userId`: current user
     - `timestamp`: current timestamp
   - Log entry is IMMUTABLE

3. **State Update**
   - Update document `governanceState`
   - Add entry to `governanceHistory[]`
   - Trigger notifications if needed

4. **Bulk Operations**
   - Multiple documents selected
   - Bulk state change
   - One log entry per document (or `bulk_action` entry)

5. **Deprecation**
   - Set `governanceState: "Deprecated"`
   - Set `supersededByVersionId` or `supersededBy`
   - Update `supersessionChain`
   - Create governance log entry with reason

---

## Solr Schema Design Requirements

### Collection Structure Recommendation

**Option 1: Single Collection with Nested Documents**
- Parent documents (File metadata)
- Child documents (Chunks)
- Pros: Single collection, atomic updates
- Cons: Complex queries, larger documents

**Option 2: Two Collections**
- `tax_documents` - Document metadata
- `tax_chunks` - Chunks with document reference
- Pros: Simpler queries, better performance
- Cons: Need to join for full document info

**Recommendation: Option 2 (Two Collections)**

### Collection 1: `tax_documents`

**Unique Key:** `id`

**Field Definitions:**

```xml
<!-- Identity Fields -->
<field name="id" type="string" indexed="true" stored="true" required="true"/>
<field name="name" type="text_general" indexed="true" stored="true"/>
<field name="documentName" type="string" indexed="true" stored="true"/>
<field name="title" type="text_general" indexed="true" stored="true"/>
<field name="excerpt" type="text_general" indexed="true" stored="true"/>

<!-- Source Tracking -->
<field name="sourceUrl" type="string" indexed="true" stored="true"/>
<field name="sourceDomain" type="string" indexed="true" stored="true" docValues="true"/>
<field name="knowledgeBaseId" type="string" indexed="true" stored="true" docValues="true"/>
<field name="knowledgeBaseName" type="string" indexed="true" stored="true"/>

<!-- Temporal Fields -->
<field name="uploadedDate" type="pdate" indexed="true" stored="true" docValues="true"/>
<field name="lastCrawled" type="pdate" indexed="true" stored="true" docValues="true"/>
<field name="effectiveFrom" type="pdate" indexed="true" stored="true" docValues="true"/>
<field name="effectiveTo" type="pdate" indexed="true" stored="true" docValues="true"/>
<field name="revisionDate" type="pdate" indexed="true" stored="true" docValues="true"/>
<field name="lastEmbedded" type="pdate" indexed="true" stored="true" docValues="true"/>

<!-- Status Fields -->
<field name="syncStatus" type="string" indexed="true" stored="true" docValues="true"/>
<field name="indexStatus" type="string" indexed="true" stored="true" docValues="true"/>
<field name="governanceState" type="string" indexed="true" stored="true" docValues="true"/>
<field name="syncError" type="text_general" indexed="true" stored="true"/>
<field name="indexError" type="text_general" indexed="true" stored="true"/>

<!-- Classification Fields -->
<field name="authorityLevel" type="pint" indexed="true" stored="true" docValues="true"/>
<field name="authorityLevelRationale" type="text_general" indexed="true" stored="true"/>
<field name="docType" type="string" indexed="true" stored="true" docValues="true"/>
<field name="formFamily" type="string" indexed="true" stored="true" docValues="true"/>
<field name="category" type="string" indexed="true" stored="true" docValues="true"/>
<field name="tags" type="string" indexed="true" stored="true" multiValued="true" docValues="true"/>

<!-- Tax & Jurisdiction -->
<field name="taxYear" type="pint" indexed="true" stored="true" docValues="true"/>
<field name="appliesToTaxYears" type="pint" indexed="true" stored="true" multiValued="true" docValues="true"/>
<field name="jurisdiction" type="string" indexed="true" stored="true" docValues="true"/>
<field name="state" type="string" indexed="true" stored="true" docValues="true"/>
<field name="appliesToJurisdictions" type="string" indexed="true" stored="true" multiValued="true" docValues="true"/>

<!-- Versioning -->
<field name="version" type="string" indexed="true" stored="true"/>
<field name="isLatestForTaxYear" type="boolean" indexed="true" stored="true" docValues="true"/>
<field name="supersededByVersionId" type="string" indexed="true" stored="true"/>
<field name="supersededBy" type="string" indexed="true" stored="true"/>
<field name="hasNewerVersion" type="boolean" indexed="true" stored="true" docValues="true"/>
<field name="replacedBy" type="string" indexed="true" stored="true"/>
<field name="supersessionChain" type="string" indexed="true" stored="true" multiValued="true"/>

<!-- RAG Metadata -->
<field name="chunkCount" type="pint" indexed="true" stored="true" docValues="true"/>
<field name="tokensIndexed" type="plong" indexed="true" stored="true" docValues="true"/>
<field name="embeddingModel" type="string" indexed="true" stored="true"/>
<field name="ragErrors" type="text_general" indexed="true" stored="true"/>

<!-- Quality Fields -->
<field name="parsingQuality" type="string" indexed="true" stored="true" docValues="true"/>
<field name="classificationConfidence" type="pfloat" indexed="true" stored="true" docValues="true"/>
<field name="needsHumanReview" type="boolean" indexed="true" stored="true" docValues="true"/>
<field name="reviewReason" type="text_general" indexed="true" stored="true"/>
<field name="reviewedAt" type="pdate" indexed="true" stored="true" docValues="true"/>
<field name="reviewedBy" type="string" indexed="true" stored="true"/>

<!-- Content (for BM25 search on document level) -->
<field name="content" type="text_general" indexed="true" stored="false"/>

<!-- Copy fields for search -->
<field name="text" type="text_general" indexed="true" stored="false" multiValued="true"/>
<copyField source="name" dest="text"/>
<copyField source="title" dest="text"/>
<copyField source="excerpt" dest="text"/>
<copyField source="content" dest="text"/>
```

### Collection 2: `tax_chunks`

**Unique Key:** `id` (chunk ID)

**Field Definitions:**

```xml
<!-- Identity -->
<field name="id" type="string" indexed="true" stored="true" required="true"/>
<field name="chunkId" type="string" indexed="true" stored="true"/>
<field name="documentId" type="string" indexed="true" stored="true" docValues="true"/>

<!-- Content -->
<field name="content" type="text_general" indexed="true" stored="true"/>
<field name="vector" type="knn_vector" indexed="true" stored="true" dimension="1536"/>

<!-- Position -->
<field name="paragraphNumber" type="pint" indexed="true" stored="true" docValues="true"/>
<field name="chunkIndex" type="pint" indexed="true" stored="true" docValues="true"/>

<!-- Document Context (denormalized for performance) -->
<field name="documentName" type="string" indexed="true" stored="true"/>
<field name="sourceUrl" type="string" indexed="true" stored="true"/>
<field name="sourceDomain" type="string" indexed="true" stored="true" docValues="true"/>
<field name="authorityLevel" type="pint" indexed="true" stored="true" docValues="true"/>
<field name="taxYear" type="pint" indexed="true" stored="true" docValues="true"/>
<field name="effectiveFrom" type="pdate" indexed="true" stored="true" docValues="true"/>
<field name="jurisdiction" type="string" indexed="true" stored="true" docValues="true"/>
<field name="state" type="string" indexed="true" stored="true" docValues="true"/>
<field name="category" type="string" indexed="true" stored="true" docValues="true"/>
<field name="docType" type="string" indexed="true" stored="true" docValues="true"/>
<field name="fileVersion" type="string" indexed="true" stored="true"/>
<field name="governanceState" type="string" indexed="true" stored="true" docValues="true"/>
<field name="isLatestForTaxYear" type="boolean" indexed="true" stored="true" docValues="true"/>

<!-- Copy fields for search -->
<field name="text" type="text_general" indexed="true" stored="false"/>
<copyField source="content" dest="text"/>
```

### Field Type Definitions

**Required Custom Field Types:**

```xml
<!-- Text field for general content -->
<fieldType name="text_general" class="solr.TextField" positionIncrementGap="100">
  <analyzer type="index">
    <tokenizer class="solr.StandardTokenizerFactory"/>
    <filter class="solr.LowerCaseFilterFactory"/>
    <filter class="solr.StopFilterFactory" words="stopwords.txt"/>
    <filter class="solr.PorterStemFilterFactory"/>
  </analyzer>
  <analyzer type="query">
    <tokenizer class="solr.StandardTokenizerFactory"/>
    <filter class="solr.LowerCaseFilterFactory"/>
    <filter class="solr.StopFilterFactory" words="stopwords.txt"/>
    <filter class="solr.PorterStemFilterFactory"/>
  </analyzer>
</fieldType>

<!-- Vector field for KNN search (Solr 9) -->
<fieldType name="knn_vector" class="solr.DenseVectorField" dimension="1536" 
           similarityFunction="cosine" knnAlgorithm="hnsw"/>
```

### Faceting Requirements

**Required Facets:**
- `authorityLevel` (int) - 6 values
- `docType` (string) - 5 values
- `jurisdiction` (string) - 3 values
- `state` (string) - 50 US states
- `category` (string) - 7 categories
- `governanceState` (string) - 4 states
- `knowledgeBaseId` (string) - Multiple KBs
- `sourceDomain` (string) - Various domains

**Facet Configuration:**
- Use `docValues="true"` for efficient faceting
- Enable range faceting on `taxYear`, dates
- Enable interval faceting on `authorityLevel`

### Sorting Requirements

**Sortable Fields:**
- `priorityRank` (ascending) - For conflict resolution
- `relevanceScore` (descending) - For search relevance
- `authorityLevel` (ascending) - Lower number = higher authority
- `taxYear` (descending) - Newer first
- `effectiveFrom` (descending) - More recent first
- `lastCrawled` (descending) - Freshness
- `timestamp` (descending) - For audit logs

### Search Requirements

**Text Search:**
- BM25 on `content`, `title`, `excerpt`
- Field boosting: `title^3`, `excerpt^1.5`, `content^2`
- Use `edismax` query parser

**Vector Search:**
- KNN search on `vector` field
- Cosine similarity
- HNSW algorithm (Solr 9)
- Top K retrieval

**Hybrid Search:**
- Combine BM25 and vector scores
- Add authority weight
- Formula: `BM25_score × α + vector_score × β + authority_weight × γ`
- Default weights: α=0.3, β=0.5, γ=0.2

**Filter Queries:**
- Exact match: `jurisdiction:"federal"`
- Range: `taxYear:[2023 TO 2024]`
- Date range: `lastCrawled:[2024-01-01T00:00:00Z TO *]`
- Boolean: `isLatestForTaxYear:true`
- Multi-value: `appliesToTaxYears:2024`

### Indexing Strategy

**Document Indexing:**
- Index document metadata immediately after sync
- Update `indexStatus` field
- Track `chunkCount`, `tokensIndexed`

**Chunk Indexing:**
- Index chunks after embedding generation
- Denormalize document metadata into chunks
- Update document `chunkCount` after chunk indexing

**Update Strategy:**
- Use atomic updates for status fields
- Full document update for metadata changes
- Incremental updates for `lastCrawled`, `lastEmbedded`

**Performance Considerations:**
- Use `docValues="true"` for faceting/sorting fields
- Use `stored="false"` for large text fields if not needed
- Index `content` field but don't store (if chunks are primary search target)
- Consider sharding by `knowledgeBaseId` or `jurisdiction`

---

## Implementation Recommendations

### 1. Collection Organization

**Recommended Structure:**
- **Collection 1:** `tax_documents` - Document metadata
- **Collection 2:** `tax_chunks` - Chunks with denormalized document fields
- **Collection 3:** `tax_governance_logs` (optional) - Audit logs

**Rationale:**
- Chunks are primary search target (RAG)
- Document metadata needed for filtering/display
- Denormalization improves query performance
- Separate collections allow independent scaling

### 2. Document-Chunk Relationship

**Approach:**
- Store `documentId` in each chunk
- Denormalize critical document fields into chunks
- Use `documentId` to join back to document collection when needed

**Denormalized Fields in Chunks:**
- `documentName`, `sourceUrl`, `sourceDomain`
- `authorityLevel`, `taxYear`, `effectiveFrom`
- `jurisdiction`, `state`, `category`, `docType`
- `governanceState`, `isLatestForTaxYear`

**Benefits:**
- Single query for search (no joins)
- Faster filtering
- Better performance for RAG queries

### 3. Versioning Strategy

**Approach:**
- Use `formFamily` + `taxYear` + `version` as composite key
- `isLatestForTaxYear` flag for quick filtering
- `supersededByVersionId` for version chain navigation

**Queries:**
- Find latest: `formFamily:"1040" AND taxYear:2024 AND isLatestForTaxYear:true`
- Find superseded: `supersededByVersionId:"2024-v2"`
- Find version chain: Query by `formFamily` and `taxYear`, sort by `version`

### 4. Authority Level Weighting

**Weight Calculation:**
```python
def calculate_authority_weight(level: int) -> float:
    """Lower level = higher weight (Level 1 = 1.0, Level 6 = 0.2)"""
    if level is None:
        return 0.5
    return (6 - min(level, 5)) / 5
```

**Usage in Scoring:**
- Include in hybrid score calculation
- Use as boost factor in queries
- Filter by authority level in search controls

### 5. Conflict Resolution Implementation

**Priority Assignment:**
1. Check `authorityLevel` (lower = higher priority)
2. Check `effectiveFrom` (more recent = higher priority)
3. Check `jurisdiction` match (exact match = higher priority)

**Solr Implementation:**
- Calculate `priorityRank` during indexing or query time
- Sort by `priorityRank` ascending
- Set `isPreferred` flag for top-ranked results

### 6. Freshness Tracking

**Staleness Calculation:**
- Compare `lastCrawled` to current date
- Flag documents with `lastCrawled` > 30 days old
- Track `hasNewerVersion` flag

**Queries:**
- Stale documents: `lastCrawled:[* TO NOW-30DAYS]`
- Needs re-crawl: `hasNewerVersion:true AND lastCrawled:[* TO NOW-30DAYS]`

### 7. Governance State Management

**State Transitions:**
- Enforce state machine rules
- Require reason for deprecation
- Create immutable log entry for each transition

**Solr Queries:**
- Published only: `governanceState:"Published"`
- Needs review: `governanceState:"Draft" AND needsHumanReview:true`
- Deprecated: `governanceState:"Deprecated"`

### 8. Search Quality Controls

**Implementation:**
- Adjust hybrid search weights based on `retrievalMode`
- Apply authority filtering based on `authorityWeightControl`
- Balance semantic/lexical based on `semanticLexicalBalance`

**Query Parameters:**
- `alpha` (BM25 weight): 0.2-0.4
- `beta` (vector weight): 0.4-0.7
- `gamma` (authority weight): 0.1-0.3
- `semanticLexicalBalance`: 0.0-1.0

### 9. Performance Optimization

**Indexing:**
- Batch index chunks (100-1000 at a time)
- Use soft commits for real-time updates
- Use hard commits periodically

**Querying:**
- Cache frequent filter combinations
- Use filter queries (`fq`) instead of query (`q`) for filters
- Limit result sets with `rows` parameter
- Use `fl` to limit returned fields

**Scaling:**
- Shard by `knowledgeBaseId` or `jurisdiction`
- Replicate for read scaling
- Consider separate collections for different document types

### 10. Compliance & Audit Trail

**Requirements:**
- Immutable governance logs
- Full document lineage tracking
- Timestamped all actions
- User attribution

**Implementation:**
- Store governance logs in separate collection or database
- Include `documentId` reference
- Enable full-text search on log entries
- Export capabilities (CSV, JSON)

---

## Appendices

### Appendix A: Complete Field Reference

[See "Data Model Specifications" section above]

### Appendix B: Enum Values Reference

[See "Data Model Specifications" section above]

### Appendix C: Query Examples

**Example 1: Basic Hybrid Search**
```
POST /solr/tax_chunks/select
{
  "q": "{!knn f=vector topK=10}[0.1, 0.2, ...]",
  "fq": [
    "jurisdiction:\"federal\"",
    "taxYear:2024",
    "governanceState:\"Published\"",
    "isLatestForTaxYear:true"
  ],
  "fl": "id,content,score,documentName,authorityLevel",
  "rows": 10
}
```

**Example 2: Authority Level Faceting**
```
POST /solr/tax_documents/select
{
  "q": "*:*",
  "facet": true,
  "facet.field": "authorityLevel",
  "facet.range": "authorityLevel",
  "facet.range.start": 1,
  "facet.range.end": 6,
  "facet.range.gap": 1
}
```

**Example 3: Stale Documents Query**
```
POST /solr/tax_documents/select
{
  "q": "*:*",
  "fq": [
    "lastCrawled:[* TO NOW-30DAYS]",
    "hasNewerVersion:true"
  ],
  "sort": "lastCrawled asc",
  "rows": 100
}
```

**Example 4: Version Chain Query**
```
POST /solr/tax_documents/select
{
  "q": "*:*",
  "fq": [
    "formFamily:\"1040\"",
    "taxYear:2024"
  ],
  "sort": "version asc",
  "fl": "id,name,version,isLatestForTaxYear,supersededByVersionId"
}
```

### Appendix D: Data Flow Diagrams

[Diagrams would be included here - see mermaid syntax in plan]

### Appendix E: Authority Level Assignment Rules

**URL Pattern Matching Rules:**

| Authority Level | URL Patterns |
|----------------|--------------|
| Level 1 | `law.cornell.edu`, `govinfo.gov`, `/irc/`, `/cfr/`, `treasury.gov/regulations` |
| Level 2 | `irs.gov/forms-pubs`, `irs.gov/forms-instructions`, `/form-` |
| Level 3 | `irs.gov/pub/irs-drop`, `revenue-ruling`, `revenue-procedure`, `/rr-`, `/rp-` |
| Level 4 | `irs.gov/faqs`, `irs.gov/publications`, `/pub/`, `/irm/` |
| Level 5 | `cch.com`, `ria.thomsonreuters.com`, `pwc.com`, `deloitte.com`, `ey.com`, `kpmg.com` |
| Level 6 | Default (all other URLs) |

### Appendix F: Governance State Machine

```
State Transitions:
  [null] → Draft (auto on ingestion)
  Draft → Under Review (manual)
  Under Review → Published (manual, after verification)
  Published → Deprecated (manual, when superseded)
  Any → Deprecated (manual, with reason)
```

### Appendix G: Citability Criteria

**Document is citable if ALL of the following are true:**
1. `governanceState === "Published"`
2. `authorityLevel <= 2`
3. `taxYear === currentTaxYear` OR `appliesToTaxYears.includes(currentTaxYear)`
4. `!supersededByVersionId && !supersededBy`
5. `parsingQuality === "ok"`

---

## Conclusion

This comprehensive analysis provides the foundation for designing a robust Solr9 schema that supports:

1. **Hybrid Search** - Semantic (vector) + Lexical (BM25) + Authority-weighted
2. **Complex Filtering** - By jurisdiction, state, category, tax year, authority level, governance state
3. **Version Management** - Supersession chains, latest version tracking
4. **RAG Pipeline** - Chunk indexing, embedding storage, relevance scoring
5. **Governance** - State management, audit logging, compliance tracking
6. **Freshness Monitoring** - Staleness detection, URL change tracking
7. **Quality Control** - Classification confidence, human review flags

The recommended two-collection approach (documents + chunks) provides optimal performance for RAG queries while maintaining document metadata for filtering and display.

**Next Steps:**
1. Review and validate field definitions
2. Create Solr schema.xml files
3. Implement indexing pipeline
4. Implement search API with hybrid scoring
5. Test with sample data
6. Performance tuning and optimization

---

**End of Report**

