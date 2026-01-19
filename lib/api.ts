/**
 * API Client for Tax Knowledge Base
 * Handles all backend API communication
 */

import type {
    FileUploadMetadata,
    FileUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    DocumentFilters,
    SearchRequest,
    SearchResponse,
} from "./types"

// API Base URL - adjust for your environment
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
    status: number
    details?: Record<string, unknown>

    constructor(message: string, status: number, details?: Record<string, unknown>) {
        super(message)
        this.name = "ApiError"
        this.status = status
        this.details = details
    }
}

/**
 * Generic fetch wrapper with error handling
 */
async function fetchApi<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`

    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                ...options.headers,
            },
        })

        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}`
            try {
                const errorData = await response.json()
                errorMessage = errorData.detail || errorData.message || errorMessage
            } catch {
                // Ignore JSON parse errors
            }
            throw new ApiError(errorMessage, response.status)
        }

        // Handle 204 No Content
        if (response.status === 204) {
            return undefined as T
        }

        return await response.json()
    } catch (error) {
        if (error instanceof ApiError) {
            throw error
        }
        throw new ApiError(
            error instanceof Error ? error.message : "Network error",
            0
        )
    }
}

// ==================== File Upload ====================

/**
 * Upload a file with metadata
 * @param file The file to upload
 * @param metadata Optional metadata for the document
 * @returns Upload response with created document
 */
export async function uploadFile(
    file: File,
    metadata?: FileUploadMetadata
): Promise<FileUploadResponse> {
    const formData = new FormData()
    formData.append("file", file)

    if (metadata) {
        formData.append("metadata", JSON.stringify(metadata))
    }

    return fetchApi<FileUploadResponse>("/api/upload", {
        method: "POST",
        body: formData,
    })
}

// ==================== Documents ====================

/**
 * List documents with optional filters
 * @param filters Optional filter parameters
 * @returns Paginated list of documents
 */
export async function listDocuments(
    filters?: DocumentFilters
): Promise<DocumentListResponse> {
    const params = new URLSearchParams()

    if (filters) {
        if (filters.query) params.append("query", filters.query)
        if (filters.jurisdiction) params.append("jurisdiction", filters.jurisdiction)
        if (filters.state) params.append("state", filters.state)
        if (filters.city) params.append("city", filters.city)
        if (filters.tax_year) params.append("tax_year", String(filters.tax_year))
        if (filters.category) {
            filters.category.forEach(c => params.append("category", c))
        }
        if (filters.authority_level) params.append("authority_level", String(filters.authority_level))
        if (filters.governance_state) params.append("governance_state", filters.governance_state)
        if (filters.doc_type) params.append("doc_type", filters.doc_type)
        if (filters.needs_human_review !== undefined) {
            params.append("needs_human_review", String(filters.needs_human_review))
        }
        if (filters.page) params.append("page", String(filters.page))
        if (filters.limit) params.append("limit", String(filters.limit))
        if (filters.sort) params.append("sort", filters.sort)
    }

    const queryString = params.toString()
    const endpoint = queryString ? `/api/documents?${queryString}` : "/api/documents"

    return fetchApi<DocumentListResponse>(endpoint)
}

/**
 * Get a single document by ID
 * @param documentId The document ID
 * @returns Document details
 */
export async function getDocument(documentId: string): Promise<DocumentResponse> {
    return fetchApi<DocumentResponse>(`/api/documents/${documentId}`)
}

/**
 * Delete a document
 * @param documentId The document ID to delete
 */
export async function deleteDocument(documentId: string): Promise<void> {
    return fetchApi<void>(`/api/documents/${documentId}`, {
        method: "DELETE",
    })
}

/**
 * Update a document
 * @param documentId The document ID
 * @param updates Fields to update
 * @returns Updated document
 */
export async function updateDocument(
    documentId: string,
    updates: Partial<DocumentResponse>
): Promise<DocumentResponse> {
    return fetchApi<DocumentResponse>(`/api/documents/${documentId}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(updates),
    })
}

// ==================== Search ====================

/**
 * Perform RAG search on the knowledge base
 * @param request Search request with query, filters, and quality controls
 * @returns Search response with retrieved chunks and source documents
 */
export async function ragSearch(request: SearchRequest): Promise<SearchResponse> {
    return fetchApi<SearchResponse>("/api/search/rag", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
    })
}

// ==================== Dashboard ====================

import type { DashboardStats } from "./types"

/**
 * Get dashboard statistics (total documents, chunks, etc.)
 * @returns Dashboard statistics from the backend
 */
export async function getDashboardStats(): Promise<DashboardStats> {
    return fetchApi<DashboardStats>("/api/dashboard/stats")
}

