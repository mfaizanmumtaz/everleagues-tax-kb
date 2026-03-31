"""Pydantic models for URL management operations."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


# ==================== Enums ====================


class DataSource(str, Enum):
    """Data source type."""

    SCRAPE = "scrape"
    FILE = "file"


class URLStatus(str, Enum):
    """URL status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SCRAPING = "scraping"


# ==================== URL Models ====================


class URLBase(BaseModel):
    """Base URL fields."""

    url: str = Field(..., description="URL to scrape")
    category: str = Field(
        default="Federal", description="Category (Federal/State/Local)"
    )
    state: Optional[str] = Field(
        default=None, description="State code if state-level or local-level"
    )
    city: Optional[str] = Field(default=None, description="City name if local-level")
    data_source: DataSource = Field(
        default=DataSource.SCRAPE, description="Data source type"
    )


class URLCreate(URLBase):
    """Request to create a URL."""

    name: Optional[str] = Field(default=None, description="Display name")
    description: Optional[str] = Field(default=None, description="Description")
    delay_between_requests: int = Field(
        default=2, ge=1, description="Seconds between requests"
    )
    max_requests_per_minute: int = Field(
        default=30, ge=1, description="Max requests per minute"
    )
    max_files_per_session: int = Field(
        default=10000, ge=1, description="Max files to download"
    )


class URLUpdate(BaseModel):
    """Request to update a URL."""

    url: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    data_source: Optional[DataSource] = None
    status: Optional[URLStatus] = None
    delay_between_requests: Optional[int] = None
    max_requests_per_minute: Optional[int] = None
    max_files_per_session: Optional[int] = None


class URLResponse(BaseModel):
    """URL response."""

    id: str
    url: str
    name: Optional[str] = None
    category: str = "Federal"
    state: Optional[str] = None
    city: Optional[str] = None
    data_source: str = "scrape"
    status: str = "active"
    last_scraped: Optional[datetime] = None
    documents_count: int = 0
    error_message: Optional[str] = None
    delay_between_requests: int = 2
    max_requests_per_minute: int = 30
    max_files_per_session: int = 10000
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class URLListResponse(BaseModel):
    """Response for URL list."""

    items: List[URLResponse]
    total: int
    page: int
    limit: int
    pages: int
    has_next: bool
    has_prev: bool


class ScrapeProgress(BaseModel):
    """Scraping progress response."""

    url_id: str
    job_id: Optional[str] = None
    status: str = "idle"
    current: int = 0
    total: int = 0
    message: str = ""
    documents_created: int = 0
    documents_failed: int = 0
    started_at: Optional[str] = None
