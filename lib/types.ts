/**
 * API Types for Tax Knowledge Base
 * Matches backend models
 */

/**
 * File Upload Metadata (sent with file upload)
 * 
 * Validation Rules:
 * - jurisdiction is REQUIRED (must be: federal, state, or local)
 * - If jurisdiction is "state" or "local": state is REQUIRED
 * - If jurisdiction is "local": city is also REQUIRED
 */
export interface FileUploadMetadata {
    jurisdiction: "federal" | "state" | "local"  // REQUIRED
    state?: string  // 2-letter code (e.g., "CA") - Required for state/local
    city?: string   // Required for local jurisdiction
    tax_year?: number
    tax_type?: string
    authority_level?: 1 | 2 | 3 | 4 | 5 | 6
    authority_level_rationale?: string
    knowledge_base_id?: string
    tags?: string[]
    title?: string
    description?: string
    doc_type?: "form" | "instructions" | "publication" | "schedule" | "regulation" | "ruling" | "notice" | "faq" | "guide" | "other"
}

// Document Response (returned from API)
export interface DocumentResponse {
    id: string
    name: string
    title?: string
    description?: string
    source_url?: string
    source_domain?: string
    tags: string[]
    category?: string
    doc_type?: string
    size?: string
    knowledge_base_id: string

    // Tax fields
    tax_year?: number
    tax_type?: string
    jurisdiction?: string
    state?: string
    city?: string
    authority_level?: number
    authority_level_rationale?: string
    form_family?: string
    effective_from?: string
    effective_to?: string

    // Status
    sync_status: "synced" | "syncing" | "sync_failed"
    index_status: "indexed" | "indexing" | "index_failed" | "not_indexed"
    sync_error?: string
    index_error?: string

    // Governance
    governance_state?: "Draft" | "Under Review" | "Published" | "Deprecated"

    // RAG
    chunk_count?: number
    tokens_indexed?: number
    embedding_model?: string
    last_indexed_at?: string

    // Review
    needs_human_review?: boolean
    review_reason?: string
    reviewed_at?: string
    reviewed_by?: string
    classification_confidence?: number

    // Timestamps
    uploaded_date?: string
    created_at?: string
    updated_at?: string
}

// File Upload Response
export interface FileUploadResponse {
    success: boolean
    message: string
    document?: DocumentResponse
}

// Document List Response
export interface DocumentListResponse {
    items: DocumentResponse[]
    total: number
    page: number
    limit: number
    pages: number
    has_next: boolean
    has_prev: boolean
}

// Filter parameters for listing documents
export interface DocumentFilters {
    query?: string
    jurisdiction?: string
    state?: string
    city?: string
    tax_year?: number
    category?: string[]
    authority_level?: number
    governance_state?: string
    doc_type?: string
    needs_human_review?: boolean
    page?: number
    limit?: number
    sort?: string
}

// ==================== Search Types ====================

// Search Quality Controls (sent to API)
export interface SearchQualityControls {
    retrieval_mode?: "hybrid" | "vector" | "bm25"
    authority_weight_control?: number  // 0-1
    semantic_lexical_balance?: number  // 0-1
    top_k?: number
}

// Search Filters
export interface SearchFilters {
    jurisdiction?: string
    state?: string
    city?: string
    category?: string[]
    tax_year?: number
    authority_level?: number
    governance_state?: string
    doc_type?: string
}

// Search Request
export interface SearchRequest {
    query: string
    filters?: SearchFilters
    search_quality_controls?: SearchQualityControls
    generate_answer?: boolean  // Default: true - Generate LLM answer from chunks
}

// Retrieved Chunk (from search results)
export interface RetrievedChunk {
    id: string
    chunk_id: string
    document_name: string
    content: string
    relevance_score: number
    authority_level?: number
    priority_rank?: number
    is_preferred: boolean
    tax_year?: number
    jurisdiction?: string
    state?: string
    source_url?: string
    source_domain?: string
    paragraph_number?: number
    file_version?: string
    effective_from?: string
    conflict_resolution_reason?: "higher_authority" | "more_recent_date" | "jurisdiction_match" | null
}

// Source Document (grouped from chunks)
export interface SourceDocument {
    id: string
    title: string
    category?: string
    jurisdiction?: string
    url?: string
    excerpt?: string
    authority_level?: number
    priority_rank?: number
    is_preferred: boolean
    tax_year?: number
    state?: string
    effective_from?: string
    conflict_resolution_reason?: "higher_authority" | "more_recent_date" | "jurisdiction_match" | null
    chunks: RetrievedChunk[]
}

// Search Response
export interface SearchResponse {
    query: string
    retrieved_chunks: RetrievedChunk[]
    source_documents: SourceDocument[]
    total_chunks: number
    search_time_ms: number
    retrieval_mode: string
    generated_answer?: string  // LLM-generated answer based on retrieved chunks
    score_weights?: { alpha: number; beta: number; gamma: number }
}

// ==================== Dashboard Types ====================

// Dashboard Statistics (from /api/dashboard/stats)
export interface DashboardStats {
    total_documents: number
    total_chunks: number
    total_tokens: number
    documents_by_governance: Record<string, number>
    documents_by_sync_status: Record<string, number>
    documents_by_index_status: Record<string, number>
    documents_by_jurisdiction: Record<string, number>
    chunks_by_jurisdiction: Record<string, number>
    chunks_by_tax_year: Record<string, number>
}

