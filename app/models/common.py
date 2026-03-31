"""Common Pydantic models for pagination and filtering."""

from typing import Optional, Generic, TypeVar, List, Any
from pydantic import BaseModel, Field, model_validator
from enum import Enum

from ..config.jurisdiction_config import (
    is_valid_state,
    is_valid_city,
    get_valid_states,
    get_valid_cities,
)


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

    @model_validator(mode="after")
    def validate_jurisdiction_requirements(self):
        """
        Validate jurisdiction-related filter requirements.
        
        This validation is optional - only triggered when jurisdiction is provided.
        Rules:
        - If jurisdiction is 'state': state code is required
        - If jurisdiction is 'local': both state code and city are required
        - State code must be a valid US state code
        - City must be valid for the specified state (if city data exists)
        """
        jurisdiction = self.jurisdiction
        state = self.state
        city = self.city

        # Only validate if jurisdiction is provided
        if jurisdiction:
            jurisdiction_lower = jurisdiction.lower()
            
            # Validate jurisdiction value itself
            valid_jurisdictions = ["federal", "state", "local"]
            if jurisdiction_lower not in valid_jurisdictions:
                raise ValueError(
                    f"Invalid jurisdiction '{jurisdiction}'. "
                    f"Must be one of: {', '.join(valid_jurisdictions)}"
                )
            
            # State jurisdiction requires state code
            if jurisdiction_lower == "state":
                if not state:
                    raise ValueError(
                        "When filtering by 'state' jurisdiction, please provide a state code "
                        "(e.g., CA, NY, TX) using the 'state' parameter"
                    )
            
            # Local jurisdiction requires both state and city
            if jurisdiction_lower == "local":
                missing = []
                if not state:
                    missing.append("state code (e.g., CA, NY)")
                if not city:
                    missing.append("city name (e.g., Los Angeles, New York)")
                if missing:
                    raise ValueError(
                        f"When filtering by 'local' jurisdiction, please provide: "
                        f"{' and '.join(missing)}"
                    )

        # Validate state code if provided (regardless of jurisdiction filter)
        if state:
            state_upper = state.upper()
            if not is_valid_state(state_upper):
                valid_states = get_valid_states()
                sample_states = sorted(valid_states)[:10]
                raise ValueError(
                    f"Invalid state code '{state}'. "
                    f"Please use a valid 2-letter US state code. "
                    f"Examples: {', '.join(sample_states)}..."
                )

        # Validate city if provided with a state
        if city and state:
            valid_cities = get_valid_cities(state.upper())
            if valid_cities and city not in valid_cities:
                # Only validate if we have city data for this state
                sample_cities = valid_cities[:5]
                raise ValueError(
                    f"Invalid city '{city}' for state '{state.upper()}'. "
                    f"Valid cities include: {', '.join(sample_cities)}"
                    f"{'...' if len(valid_cities) > 5 else ''}"
                )

        return self


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
