"""Pydantic models for URL management operations."""

from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum

from ..config.jurisdiction_config import (
    is_valid_state,
    get_valid_states,
    get_valid_cities,
)


# ==================== Enums ====================

JurisdictionType = Literal["federal", "state", "local"]


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
    jurisdiction: JurisdictionType = Field(
        default="federal", description="Jurisdiction level (federal/state/local)"
    )
    state: Optional[str] = Field(
        default=None, description="State code if state-level or local-level"
    )
    city: Optional[str] = Field(default=None, description="City name if local-level")
    data_source: DataSource = Field(
        default=DataSource.SCRAPE, description="Data source type"
    )

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip().upper()
            if not is_valid_state(v):
                valid_states = get_valid_states()
                raise ValueError(
                    f'Invalid state code "{v}". '
                    f"Valid codes: {', '.join(sorted(valid_states))}"
                )
            return v
        return v

    @field_validator("city")
    @classmethod
    def validate_city_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("City name cannot be blank")
        return v

    @model_validator(mode="after")
    def validate_jurisdiction_requirements(self):
        jurisdiction = self.jurisdiction
        state = self.state
        city = self.city

        if jurisdiction == "state":
            if not state:
                raise ValueError(
                    "State code is required when jurisdiction is 'state' "
                    "(e.g., CA, NY, TX)"
                )

        if jurisdiction == "local":
            missing = []
            if not state:
                missing.append("state code (e.g., CA, NY)")
            if not city:
                missing.append("city name (e.g., Los Angeles, New York City)")
            if missing:
                raise ValueError(
                    f"When jurisdiction is 'local', please provide: "
                    f"{' and '.join(missing)}"
                )

        if city and state:
            valid_cities = get_valid_cities(state.upper())
            if valid_cities and city not in valid_cities:
                sample = valid_cities[:5]
                raise ValueError(
                    f"Invalid city '{city}' for state '{state.upper()}'. "
                    f"Valid cities include: {', '.join(sample)}"
                    f"{'...' if len(valid_cities) > 5 else ''}"
                )

        if jurisdiction == "federal":
            if state:
                raise ValueError(
                    "State should not be provided for federal jurisdiction"
                )
            if city:
                raise ValueError(
                    "City should not be provided for federal jurisdiction"
                )

        return self


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
    jurisdiction: Optional[JurisdictionType] = None
    state: Optional[str] = None
    city: Optional[str] = None
    data_source: Optional[DataSource] = None
    status: Optional[URLStatus] = None
    delay_between_requests: Optional[int] = None
    max_requests_per_minute: Optional[int] = None
    max_files_per_session: Optional[int] = None

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip().upper()
            if not is_valid_state(v):
                valid_states = get_valid_states()
                raise ValueError(
                    f'Invalid state code "{v}". '
                    f"Valid codes: {', '.join(sorted(valid_states))}"
                )
            return v
        return v

    @field_validator("city")
    @classmethod
    def validate_city_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("City name cannot be blank")
        return v

    @model_validator(mode="after")
    def validate_jurisdiction_requirements(self):
        jurisdiction = self.jurisdiction
        state = self.state
        city = self.city

        if jurisdiction == "state":
            if not state:
                raise ValueError(
                    "State code is required when jurisdiction is 'state' "
                    "(e.g., CA, NY, TX)"
                )

        if jurisdiction == "local":
            missing = []
            if not state:
                missing.append("state code (e.g., CA, NY)")
            if not city:
                missing.append("city name (e.g., Los Angeles, New York City)")
            if missing:
                raise ValueError(
                    f"When jurisdiction is 'local', please provide: "
                    f"{' and '.join(missing)}"
                )

        if city and state:
            valid_cities = get_valid_cities(state.upper())
            if valid_cities and city not in valid_cities:
                sample = valid_cities[:5]
                raise ValueError(
                    f"Invalid city '{city}' for state '{state.upper()}'. "
                    f"Valid cities include: {', '.join(sample)}"
                    f"{'...' if len(valid_cities) > 5 else ''}"
                )

        if jurisdiction == "federal":
            if state:
                raise ValueError(
                    "State should not be provided for federal jurisdiction"
                )
            if city:
                raise ValueError(
                    "City should not be provided for federal jurisdiction"
                )

        return self


class URLResponse(BaseModel):
    """URL response."""

    id: str
    url: str
    name: Optional[str] = None
    jurisdiction: str = "federal"
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
