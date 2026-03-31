"""Pydantic models for Search operations."""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from .common import FilterParams


class SearchQualityControls(BaseModel):
    """Search quality control parameters."""

    retrieval_mode: Literal["hybrid", "vector", "bm25"] = Field(
        default="hybrid",
        description="Search mode: hybrid (default), vector-only, or BM25-only",
    )
    authority_weight_control: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for authority level in scoring (0-1)",
    )
    semantic_lexical_balance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Balance between semantic and lexical search (0=lexical, 1=semantic)",
    )
    top_k: int = Field(
        default=10, ge=1, le=100, description="Number of results to return"
    )


class SearchRequest(BaseModel):
    """Request model for RAG search."""

    query: str = Field(..., min_length=1, description="Search query text")
    filters: Optional[FilterParams] = Field(
        default=None, description="Optional filters"
    )
    search_quality_controls: Optional[SearchQualityControls] = Field(
        default=None, description="Search quality control parameters"
    )


class RetrievedChunk(BaseModel):
    """A retrieved chunk from search results."""

    id: str
    chunk_id: str
    document_name: str
    content: str
    relevance_score: float = Field(description="Combined relevance score")

    # Authority and ranking
    authority_level: Optional[int] = Field(default=None, ge=1, le=6)
    priority_rank: Optional[int] = Field(default=None, description="Rank in results")
    is_preferred: bool = Field(
        default=False, description="Whether this is the preferred chunk"
    )

    # Tax metadata
    tax_year: Optional[int] = None
    jurisdiction: Optional[str] = None
    state: Optional[str] = None

    # Source information
    source_url: Optional[str] = None
    source_domain: Optional[str] = None

    # Position metadata
    paragraph_number: Optional[int] = None
    file_version: Optional[str] = None

    # Temporal metadata
    effective_from: Optional[datetime] = None

    # Conflict resolution
    conflict_resolution_reason: Optional[
        Literal["higher_authority", "more_recent_date", "jurisdiction_match"]
    ] = None

    class Config:
        from_attributes = True


class SourceDocument(BaseModel):
    """A source document referenced in search results."""

    id: str
    title: str
    jurisdiction: Optional[str] = None
    url: Optional[str] = None
    excerpt: Optional[str] = None

    # Authority and ranking
    authority_level: Optional[int] = Field(default=None, ge=1, le=6)
    priority_rank: Optional[int] = None
    is_preferred: bool = False

    # Tax metadata
    tax_year: Optional[int] = None
    state: Optional[str] = None
    effective_from: Optional[datetime] = None

    # Conflict resolution
    conflict_resolution_reason: Optional[
        Literal["higher_authority", "more_recent_date", "jurisdiction_match"]
    ] = None

    # Associated chunks
    chunks: List[RetrievedChunk] = Field(default_factory=list)

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Response model for RAG search."""

    query: str
    retrieved_chunks: List[RetrievedChunk]
    source_documents: List[SourceDocument]
    total_chunks: int = Field(description="Total number of matching chunks")
    search_time_ms: float = Field(description="Search execution time in milliseconds")
    retrieval_mode: str = Field(description="Search mode used")

    # Score breakdown for debugging
    score_weights: Optional[dict] = Field(
        default=None, description="Weights used for scoring (alpha, beta, gamma)"
    )


class ChunkSearchParams(BaseModel):
    """Parameters for chunk-specific search."""

    query: Optional[str] = Field(default=None, description="Text query")
    document_id: Optional[str] = Field(
        default=None, description="Filter by document ID"
    )
    filters: Optional[FilterParams] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
