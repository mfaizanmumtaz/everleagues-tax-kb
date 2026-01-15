"""Pydantic models for Document operations."""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from .common import GovernanceState, SyncStatus, IndexStatus


class IngestionHistoryEvent(BaseModel):
    """Event in document ingestion history."""

    timestamp: datetime
    event: str
    details: Optional[str] = None


class ErrorHistoryEvent(BaseModel):
    """Event in document error history."""

    timestamp: datetime
    error_type: str
    message: str
    resolved: bool = False


class GovernanceHistoryEvent(BaseModel):
    """Event in document governance history."""

    timestamp: datetime
    from_state: Optional[str] = None
    to_state: str
    changed_by: str
    reason: Optional[str] = None


class DocumentBase(BaseModel):
    """Base document fields."""

    name: str = Field(..., description="Document filename")
    title: Optional[str] = Field(default=None, description="Document title")
    description: Optional[str] = Field(default=None, description="Document description")
    source_url: Optional[str] = Field(default=None, description="Source URL")
    source_domain: Optional[str] = Field(default=None, description="Source domain")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    category: Optional[str] = Field(default=None, description="Document category")
    doc_type: Optional[str] = Field(default=None, description="Document type")

    # Tax-specific fields
    tax_year: Optional[int] = Field(default=None, description="Applicable tax year")
    tax_type: Optional[str] = Field(default=None, description="Tax type")
    jurisdiction: Optional[str] = Field(default=None, description="Jurisdiction level")
    state: Optional[str] = Field(default=None, description="State code")
    city: Optional[str] = Field(default=None, description="City name")
    authority_level: Optional[int] = Field(
        default=None, ge=1, le=6, description="Authority level (1-6)"
    )
    authority_level_rationale: Optional[str] = Field(
        default=None, description="Rationale for authority level"
    )

    # Temporal fields
    effective_from: Optional[datetime] = Field(
        default=None, description="Effective start date"
    )
    effective_to: Optional[datetime] = Field(
        default=None, description="Effective end date"
    )
    applies_to_tax_years: List[int] = Field(
        default_factory=list, description="Applicable tax years"
    )
    applies_to_jurisdictions: List[str] = Field(
        default_factory=list, description="Applicable jurisdictions"
    )
    form_family: Optional[str] = Field(
        default=None, description="Form family (e.g., 1040, SchC)"
    )


class DocumentCreate(DocumentBase):
    """Request model for creating a document."""

    size: Optional[str] = Field(default=None, description="File size")
    knowledge_base_id: str = Field(default="default", description="Knowledge base ID")


class DocumentUpdate(BaseModel):
    """Request model for updating a document."""

    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    doc_type: Optional[str] = None
    tax_year: Optional[int] = None
    tax_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    authority_level: Optional[int] = Field(default=None, ge=1, le=6)
    authority_level_rationale: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    applies_to_tax_years: Optional[List[int]] = None
    applies_to_jurisdictions: Optional[List[str]] = None
    form_family: Optional[str] = None
    superseded_by: Optional[str] = None


class GovernanceStateUpdate(BaseModel):
    """Request model for updating governance state."""

    governance_state: GovernanceState
    changed_by: str = Field(..., description="User who changed the state")
    reason: Optional[str] = Field(default=None, description="Reason for change")


class DocumentResponse(DocumentBase):
    """Response model for a document."""

    id: str
    size: Optional[str] = None
    knowledge_base_id: str = "default"

    # Status fields
    sync_status: SyncStatus = SyncStatus.SYNCED
    index_status: IndexStatus = IndexStatus.NOT_INDEXED
    sync_error: Optional[str] = None
    index_error: Optional[str] = None

    # Governance fields
    governance_state: GovernanceState = GovernanceState.DRAFT

    # RAG metadata
    chunk_count: int = 0
    tokens_indexed: int = 0
    embedding_model: Optional[str] = None
    last_indexed_at: Optional[datetime] = None

    # Review fields
    needs_human_review: bool = False
    review_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None

    # Quality fields
    parsing_quality: Optional[float] = None
    classification_confidence: Optional[float] = None

    # Version fields
    version: int = 1
    superseded_by: Optional[str] = None
    is_latest_for_tax_year: bool = True
    has_newer_version: bool = False

    # Timestamps
    uploaded_date: Optional[datetime] = None
    last_synced: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # History (stored as JSON in Solr)
    ingestion_history: List[IngestionHistoryEvent] = Field(default_factory=list)
    error_history: List[ErrorHistoryEvent] = Field(default_factory=list)
    governance_history: List[GovernanceHistoryEvent] = Field(default_factory=list)

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response model for document list."""

    items: List[DocumentResponse]
    total: int
    page: int
    limit: int
    pages: int
    has_next: bool
    has_prev: bool
