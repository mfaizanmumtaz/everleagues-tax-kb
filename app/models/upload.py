"""Pydantic models for file upload operations."""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from .document import DocumentResponse
from ..config.jurisdiction_config import (
    get_valid_states,
    get_valid_doc_types,
    get_valid_cities,
    is_valid_state,
    is_valid_city,
)


# Valid jurisdiction values
JurisdictionType = Literal["federal", "state", "local"]


class FileUploadMetadata(BaseModel):
    """Metadata for file upload (parsed from JSON form data).

    Validation Rules:
    - jurisdiction is REQUIRED (must be: federal, state, or local)
    - If jurisdiction is "state" or "local": state is REQUIRED
    - If jurisdiction is "local": city is also REQUIRED
    """

    jurisdiction: JurisdictionType = Field(
        ..., description="Document jurisdiction (federal/state/local) - REQUIRED"
    )
    state: Optional[str] = Field(
        default=None, description="State code (e.g., CA, NY) - Required for state/local"
    )
    city: Optional[str] = Field(
        default=None, description="City name - Required for local jurisdiction"
    )
    tax_year: Optional[int] = Field(default=None, description="Applicable tax year")
    tax_type: Optional[str] = Field(default=None, description="Tax type")
    authority_level: Optional[int] = Field(
        default=None, ge=1, le=6, description="Authority level (1-6)"
    )
    authority_level_rationale: Optional[str] = Field(
        default=None, description="Rationale for authority level"
    )
    knowledge_base_id: str = Field(default="default", description="Knowledge base ID")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    title: Optional[str] = Field(default=None, description="Document title")
    description: Optional[str] = Field(default=None, description="Document description")
    doc_type: Optional[str] = Field(default=None, description="Document type")

    effective_from: Optional[str] = Field(
        default=None, description="Effective start date (ISO 8601)"
    )
    effective_to: Optional[str] = Field(
        default=None, description="Effective end date (ISO 8601)"
    )
    applies_to_tax_years: List[int] = Field(
        default_factory=list, description="List of applicable tax years"
    )
    applies_to_jurisdictions: List[str] = Field(
        default_factory=list, description="List of applicable jurisdictions"
    )
    form_family: Optional[str] = Field(
        default=None, description="Form family identifier (e.g. 1040, SchC)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "jurisdiction": "state",
                "state": "CA",
                "tax_year": 2024,
                "tags": ["sales-tax", "california"],
                "doc_type": "form",
            }
        }

    @model_validator(mode="after")
    def validate_jurisdiction_requirements(self):
        """Validate that state and city are provided based on jurisdiction."""
        jurisdiction = self.jurisdiction
        state = self.state
        city = self.city

        # State jurisdiction requires state
        if jurisdiction == "state":
            if not state:
                raise ValueError(
                    "state is required when jurisdiction is 'state'"
                )

        # Local jurisdiction requires both state and city
        if jurisdiction == "local":
            if not state:
                raise ValueError(
                    "state is required when jurisdiction is 'local'"
                )
            if not city:
                raise ValueError(
                    "city is required when jurisdiction is 'local'"
                )
            # Validate city is valid for the given state
            if state and city:
                valid_cities = get_valid_cities(state.upper())
                if valid_cities and city not in valid_cities:
                    # Only validate if we have city data for this state
                    raise ValueError(
                        f"Invalid city '{city}' for state '{state.upper()}'. "
                        f"Valid cities include: {', '.join(valid_cities[:5])}{'...' if len(valid_cities) > 5 else ''}"
                    )

        return self

    @field_validator("state")
    @classmethod
    def validate_state(cls, v):
        if v:
            v = v.upper()
            if not is_valid_state(v):
                valid_states = get_valid_states()
                raise ValueError(
                    f'Invalid state code "{v}". Valid codes: {", ".join(sorted(valid_states))}'
                )
            return v
        return v

    @field_validator("tax_year")
    @classmethod
    def validate_tax_year(cls, v):
        if v and (v < 1900 or v > 2100):
            raise ValueError("Tax year must be between 1900 and 2100")
        return v

    @field_validator("doc_type")
    @classmethod
    def validate_doc_type(cls, v):
        if v:
            valid_types = get_valid_doc_types()
            if v.lower() not in valid_types:
                raise ValueError(
                    f"Document type must be one of: {', '.join(valid_types)}"
                )
            return v.lower()
        return v


class FileUploadResponse(BaseModel):
    """Response after successful file upload and processing."""

    document_id: str = Field(..., description="Created document ID")
    uploaded_file_id: Optional[str] = Field(
        default=None, description="Deprecated - use registry_id instead"
    )
    registry_id: Optional[str] = Field(
        default=None, description="Document registry ID (primary tracking ID)"
    )
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    blob_path: str = Field(..., description="Path to file in blob storage")
    blob_url: str = Field(..., description="URL to access file in blob storage")
    content_type: str = Field(..., description="MIME type of the file")
    status: str = Field(
        ..., description="Processing status: uploaded, processing, indexed, or failed"
    )
    chunks_created: int = Field(default=0, description="Number of chunks created")
    word_count: int = Field(default=0, description="Total word count in extracted text")
    page_count: int = Field(
        default=0, description="Number of pages/documents extracted"
    )
    parsing_quality: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Text extraction quality score"
    )
    message: str = Field(..., description="Status message")
    document: Optional[DocumentResponse] = Field(
        default=None, description="Full document details (None while processing)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "uuid-here",
                "uploaded_file_id": "uuid-here",
                "registry_id": "uuid-here",
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
                "document": {},
            }
        }
