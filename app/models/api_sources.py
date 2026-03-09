"""Pydantic models for API source configuration operations."""

from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


# ==================== Enums ====================


class SourceCategory(str, Enum):
    """API source category."""

    FEDERAL = "federal"
    STATE = "state"
    LOCAL = "local"
    FORMS = "forms"


class SourceStatus(str, Enum):
    """API source status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"


class SourceAuthType(str, Enum):
    """Authentication type."""

    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    OAUTH = "oauth"
    NONE = "none"


class SourceFetchFrequency(str, Enum):
    """Fetch frequency."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# ==================== API Source Models ====================


class ApiSourceCreate(BaseModel):
    """Request to create an API source."""

    name: str = Field(..., min_length=1, max_length=255, description="Source name")
    description: Optional[str] = Field(default=None, description="Description")
    api_endpoint: str = Field(..., min_length=1, description="External API URL")
    category: SourceCategory = Field(
        default=SourceCategory.FEDERAL, description="Source category"
    )
    auth_type: SourceAuthType = Field(
        default=SourceAuthType.API_KEY, description="Authentication type"
    )
    api_key: Optional[str] = Field(default=None, description="API key (stored encrypted)")
    oauth_token: Optional[str] = Field(
        default=None, description="OAuth token (stored encrypted)"
    )
    custom_headers: Optional[Dict[str, str]] = Field(
        default=None, description="Custom HTTP headers"
    )
    fetch_frequency: SourceFetchFrequency = Field(
        default=SourceFetchFrequency.DAILY, description="How often to fetch"
    )
    max_file_size_mb: int = Field(
        default=50, ge=1, le=500, description="Max file size in MB"
    )


class ApiSourceUpdate(BaseModel):
    """Request to update an API source."""

    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    api_endpoint: Optional[str] = None
    category: Optional[SourceCategory] = None
    status: Optional[SourceStatus] = None
    auth_type: Optional[SourceAuthType] = None
    api_key: Optional[str] = Field(
        default=None, description="New API key (pass empty string to clear)"
    )
    oauth_token: Optional[str] = Field(
        default=None, description="New OAuth token (pass empty string to clear)"
    )
    custom_headers: Optional[Dict[str, str]] = None
    fetch_frequency: Optional[SourceFetchFrequency] = None
    max_file_size_mb: Optional[int] = Field(default=None, ge=1, le=500)


class ApiSourceResponse(BaseModel):
    """API source response (credentials masked)."""

    id: str
    name: str
    description: Optional[str] = None
    api_endpoint: str
    category: str = "federal"
    status: str = "active"
    auth_type: str = "api_key"
    api_key_configured: bool = False
    oauth_token_configured: bool = False
    custom_headers: Optional[Dict[str, str]] = None
    fetch_frequency: str = "daily"
    max_file_size_mb: int = 50
    last_fetched_at: Optional[datetime] = None
    total_files_pushed: int = 0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApiSourceListResponse(BaseModel):
    """Paginated API source list response."""

    items: List[ApiSourceResponse]
    total: int
    page: int
    limit: int
    pages: int
    has_next: bool
    has_prev: bool
