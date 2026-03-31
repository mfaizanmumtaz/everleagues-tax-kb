"""Pydantic models for Chunk operations."""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from .common import GovernanceState


class ChunkBase(BaseModel):
    """Base chunk fields."""
    content: str = Field(..., description="Chunk text content")
    document_id: str = Field(..., description="Parent document ID")
    chunk_index: int = Field(..., ge=0, description="Position in document")
    
    # Denormalized document fields
    document_name: Optional[str] = Field(default=None, description="Parent document name")
    title: Optional[str] = Field(default=None, description="Parent document title")
    source_url: Optional[str] = Field(default=None, description="Source URL")
    source_domain: Optional[str] = Field(default=None, description="Source domain")
    doc_type: Optional[str] = Field(default=None, description="Document type")
    
    # Tax-specific denormalized fields
    tax_year: Optional[int] = Field(default=None, description="Applicable tax year")
    tax_type: Optional[str] = Field(default=None, description="Tax type")
    jurisdiction: Optional[str] = Field(default=None, description="Jurisdiction level")
    state: Optional[str] = Field(default=None, description="State code")
    city: Optional[str] = Field(default=None, description="City name")
    authority_level: Optional[int] = Field(default=None, ge=1, le=6, description="Authority level (1-6)")
    
    # Governance denormalized field
    governance_state: Optional[GovernanceState] = Field(default=None, description="Document governance state")
    is_latest_for_tax_year: bool = Field(default=True, description="Latest version flag")


class ChunkCreate(ChunkBase):
    """Request model for creating a chunk."""
    vector: Optional[List[float]] = Field(default=None, description="Embedding vector (1536 dimensions)")
    
    # Optional metadata
    paragraph_number: Optional[int] = Field(default=None, description="Paragraph number in source")
    section_title: Optional[str] = Field(default=None, description="Section title")
    page_number: Optional[int] = Field(default=None, description="Page number in source")


class ChunkUpdate(BaseModel):
    """Request model for updating a chunk."""
    content: Optional[str] = None
    vector: Optional[List[float]] = None
    paragraph_number: Optional[int] = None
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    
    # Denormalized fields can be updated when parent document changes
    document_name: Optional[str] = None
    title: Optional[str] = None
    source_url: Optional[str] = None
    source_domain: Optional[str] = None
    doc_type: Optional[str] = None
    tax_year: Optional[int] = None
    tax_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    authority_level: Optional[int] = Field(default=None, ge=1, le=6)
    governance_state: Optional[GovernanceState] = None
    is_latest_for_tax_year: Optional[bool] = None


class ChunkResponse(ChunkBase):
    """Response model for a chunk."""
    id: str
    chunk_id: str = Field(..., description="Unique chunk identifier")
    
    # Vector field
    vector: Optional[List[float]] = Field(default=None, description="Embedding vector")
    
    # Metadata
    paragraph_number: Optional[int] = None
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    token_count: Optional[int] = Field(default=None, description="Number of tokens")
    char_count: Optional[int] = Field(default=None, description="Number of characters")
    
    # Timestamps
    indexed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ChunkListResponse(BaseModel):
    """Response model for chunk list."""
    items: List[ChunkResponse]
    total: int
    page: int
    limit: int
    pages: int
    has_next: bool
    has_prev: bool


class BulkChunkCreate(BaseModel):
    """Request model for bulk chunk creation."""
    chunks: List[ChunkCreate] = Field(..., description="List of chunks to create")
    generate_embeddings: bool = Field(default=True, description="Auto-generate embeddings")


class BulkChunkResponse(BaseModel):
    """Response model for bulk chunk creation."""
    created: int = Field(description="Number of chunks created")
    failed: int = Field(description="Number of chunks that failed")
    errors: List[str] = Field(default_factory=list, description="Error messages")

