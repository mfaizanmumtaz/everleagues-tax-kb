"""Common Pydantic models for pagination and filtering."""

from typing import Optional, Generic, TypeVar, List, Any
from pydantic import BaseModel, Field
from enum import Enum


class GovernanceState(str, Enum):
    """Valid governance states for documents."""

    DRAFT = "Draft"
    UNDER_REVIEW = "Under Review"
    PUBLISHED = "Published"
    DEPRECATED = "Deprecated"
    ARCHIVED = "Archived"


class SyncStatus(str, Enum):
    """Document sync status."""

    SYNCED = "synced"
    SYNCING = "syncing"
    SYNC_FAILED = "sync_failed"


class IndexStatus(str, Enum):
    """Document index status."""

    INDEXED = "indexed"
    INDEXING = "indexing"
    INDEX_FAILED = "index_failed"
    NOT_INDEXED = "not_indexed"


class JurisdictionLevel(str, Enum):
    """Jurisdiction levels."""

    FEDERAL = "federal"
    STATE = "state"
    LOCAL = "local"


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for Solr query."""
        return (self.page - 1) * self.limit


class FilterParams(BaseModel):
    """Common filter parameters for queries."""

    jurisdiction: Optional[str] = Field(
        default=None, description="Filter by jurisdiction (federal, state, local)"
    )
    state: Optional[str] = Field(
        default=None, description="Filter by state code (e.g., CA, NY)"
    )
    city: Optional[str] = Field(default=None, description="Filter by city")
    tax_year: Optional[int] = Field(default=None, description="Filter by tax year")
    category: Optional[List[str]] = Field(
        default=None, description="Filter by category"
    )
    authority_level: Optional[int] = Field(
        default=None, ge=1, le=6, description="Filter by authority level (1-6)"
    )
    governance_state: Optional[GovernanceState] = Field(
        default=None, description="Filter by governance state"
    )
    doc_type: Optional[str] = Field(default=None, description="Filter by document type")
    source_domain: Optional[str] = Field(
        default=None, description="Filter by source domain"
    )
    needs_human_review: Optional[bool] = Field(
        default=None, description="Filter by review status"
    )
    is_latest_for_tax_year: Optional[bool] = Field(
        default=None, description="Filter for latest version only"
    )


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: List[T]
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    limit: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_prev: bool = Field(description="Whether there is a previous page")


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    code: Optional[str] = None
    field: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response."""

    message: str
    data: Optional[Any] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str
    solr_documents: bool
    solr_chunks: bool
    version: str = "1.0.0"
