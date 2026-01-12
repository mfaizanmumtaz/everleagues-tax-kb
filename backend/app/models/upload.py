"""Pydantic models for file upload operations."""

from typing import Optional, List
from pydantic import BaseModel, Field
from .document import DocumentResponse


class FileUploadMetadata(BaseModel):
    """Metadata for file upload (parsed from JSON form data)."""
    
    category: Optional[str] = Field(default=None, description="Document category")
    state: Optional[str] = Field(default=None, description="State code")
    city: Optional[str] = Field(default=None, description="City name")
    tax_year: Optional[int] = Field(default=None, description="Applicable tax year")
    jurisdiction: Optional[str] = Field(default=None, description="Jurisdiction level")
    tax_type: Optional[str] = Field(default=None, description="Tax type")
    authority_level: Optional[int] = Field(default=None, ge=1, le=6, description="Authority level (1-6)")
    authority_level_rationale: Optional[str] = Field(default=None, description="Rationale for authority level")
    knowledge_base_id: str = Field(default="default", description="Knowledge base ID")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    title: Optional[str] = Field(default=None, description="Document title")
    description: Optional[str] = Field(default=None, description="Document description")
    doc_type: Optional[str] = Field(default=None, description="Document type")
    
    class Config:
        json_schema_extra = {
            "example": {
                "category": "State",
                "state": "CA",
                "tax_year": 2024,
                "jurisdiction": "State",
                "tags": ["sales-tax", "california"]
            }
        }


class FileUploadResponse(BaseModel):
    """Response after successful file upload and processing."""
    
    document_id: str = Field(..., description="Created document ID")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    blob_path: str = Field(..., description="Path to file in blob storage")
    blob_url: str = Field(..., description="URL to access file in blob storage")
    content_type: str = Field(..., description="MIME type of the file")
    status: str = Field(..., description="Processing status: uploaded, processing, indexed, or failed")
    chunks_created: int = Field(default=0, description="Number of chunks created")
    word_count: int = Field(default=0, description="Total word count in extracted text")
    page_count: int = Field(default=0, description="Number of pages/documents extracted")
    parsing_quality: float = Field(default=0.0, ge=0.0, le=1.0, description="Text extraction quality score")
    message: str = Field(..., description="Status message")
    document: DocumentResponse = Field(..., description="Full document details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "uuid-here",
                "filename": "tax-document.pdf",
                "file_size": 1024000,
                "blob_path": "uploads/uuid.pdf",
                "blob_url": "https://...",
                "content_type": "application/pdf",
                "status": "indexed",
                "chunks_created": 45,
                "word_count": 12500,
                "page_count": 10,
                "parsing_quality": 0.95,
                "message": "File uploaded and indexed successfully",
                "document": {}
            }
        }
