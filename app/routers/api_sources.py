"""API Source Configuration management routes."""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
import math

from ..database.connection import get_db
from ..services.api_source_service import ApiSourceService
from ..db_models.api_source import (
    ApiSourceCategory as DbCategory,
    ApiSourceStatus as DbStatus,
    AuthType as DbAuthType,
    FetchFrequency as DbFrequency,
)

router = APIRouter(prefix="/sources", tags=["API Sources"])


# ==================== Pydantic Models ====================


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


# ==================== Helper Functions ====================


def _map_category(value: SourceCategory) -> DbCategory:
    """Map API category to DB enum."""
    mapping = {
        SourceCategory.FEDERAL: DbCategory.FEDERAL,
        SourceCategory.STATE: DbCategory.STATE,
        SourceCategory.LOCAL: DbCategory.LOCAL,
        SourceCategory.FORMS: DbCategory.FORMS,
    }
    return mapping.get(value, DbCategory.FEDERAL)


def _map_status(value: SourceStatus) -> DbStatus:
    """Map API status to DB enum."""
    mapping = {
        SourceStatus.ACTIVE: DbStatus.ACTIVE,
        SourceStatus.INACTIVE: DbStatus.INACTIVE,
        SourceStatus.PAUSED: DbStatus.PAUSED,
    }
    return mapping.get(value, DbStatus.ACTIVE)


def _map_auth_type(value: SourceAuthType) -> DbAuthType:
    """Map API auth type to DB enum."""
    mapping = {
        SourceAuthType.API_KEY: DbAuthType.API_KEY,
        SourceAuthType.BEARER: DbAuthType.BEARER,
        SourceAuthType.BASIC: DbAuthType.BASIC,
        SourceAuthType.OAUTH: DbAuthType.OAUTH,
        SourceAuthType.NONE: DbAuthType.NONE,
    }
    return mapping.get(value, DbAuthType.API_KEY)


def _map_frequency(value: SourceFetchFrequency) -> DbFrequency:
    """Map API frequency to DB enum."""
    mapping = {
        SourceFetchFrequency.HOURLY: DbFrequency.HOURLY,
        SourceFetchFrequency.DAILY: DbFrequency.DAILY,
        SourceFetchFrequency.WEEKLY: DbFrequency.WEEKLY,
        SourceFetchFrequency.MONTHLY: DbFrequency.MONTHLY,
    }
    return mapping.get(value, DbFrequency.DAILY)


# ==================== API Endpoints ====================


@router.post("", response_model=ApiSourceResponse, status_code=201)
async def create_api_source(
    data: ApiSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new API source configuration."""
    service = ApiSourceService(db)

    source = await service.create(
        name=data.name,
        description=data.description,
        api_endpoint=data.api_endpoint,
        category=_map_category(data.category),
        auth_type=_map_auth_type(data.auth_type),
        api_key=data.api_key,
        oauth_token=data.oauth_token,
        custom_headers=data.custom_headers,
        fetch_frequency=_map_frequency(data.fetch_frequency),
        max_file_size_mb=data.max_file_size_mb,
    )

    return service.to_response_dict(source)


@router.get("", response_model=ApiSourceListResponse)
async def list_api_sources(
    category: Optional[SourceCategory] = Query(
        default=None, description="Filter by category"
    ),
    status: Optional[SourceStatus] = Query(
        default=None, description="Filter by status"
    ),
    search: Optional[str] = Query(
        default=None, description="Search in name, description, endpoint"
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """List all configured API sources with filtering and pagination."""
    service = ApiSourceService(db)

    db_category = _map_category(category) if category else None
    db_status = _map_status(status) if status else None

    sources, total = await service.list_all(
        category=db_category,
        status=db_status,
        search=search,
        page=page,
        limit=limit,
    )

    total_pages = math.ceil(total / limit) if total > 0 else 1

    return ApiSourceListResponse(
        items=[service.to_response_dict(s) for s in sources],
        total=total,
        page=page,
        limit=limit,
        pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.get("/{source_id}", response_model=ApiSourceResponse)
async def get_api_source(
    source_id: str = Path(..., description="API source ID"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single API source configuration."""
    service = ApiSourceService(db)

    try:
        uuid_id = UUID(source_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid source ID format")

    source = await service.get_by_id(uuid_id)
    if not source:
        raise HTTPException(status_code=404, detail="API source not found")

    return service.to_response_dict(source)


@router.put("/{source_id}", response_model=ApiSourceResponse)
async def update_api_source(
    data: ApiSourceUpdate,
    source_id: str = Path(..., description="API source ID"),
    db: AsyncSession = Depends(get_db),
):
    """Update an API source configuration."""
    service = ApiSourceService(db)

    try:
        uuid_id = UUID(source_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid source ID format")

    # Build update kwargs
    update_kwargs = {}

    if data.name is not None:
        update_kwargs["name"] = data.name
    if data.description is not None:
        update_kwargs["description"] = data.description
    if data.api_endpoint is not None:
        update_kwargs["api_endpoint"] = data.api_endpoint
    if data.category is not None:
        update_kwargs["category"] = _map_category(data.category)
    if data.status is not None:
        update_kwargs["status"] = _map_status(data.status)
    if data.auth_type is not None:
        update_kwargs["auth_type"] = _map_auth_type(data.auth_type)
    if data.api_key is not None:
        update_kwargs["api_key"] = data.api_key if data.api_key else None
    if data.oauth_token is not None:
        update_kwargs["oauth_token"] = data.oauth_token if data.oauth_token else None
    if data.custom_headers is not None:
        update_kwargs["custom_headers"] = data.custom_headers
    if data.fetch_frequency is not None:
        update_kwargs["fetch_frequency"] = _map_frequency(data.fetch_frequency)
    if data.max_file_size_mb is not None:
        update_kwargs["max_file_size_mb"] = data.max_file_size_mb

    source = await service.update(uuid_id, **update_kwargs)
    if not source:
        raise HTTPException(status_code=404, detail="API source not found")

    return service.to_response_dict(source)


@router.delete("/{source_id}", status_code=204)
async def delete_api_source(
    source_id: str = Path(..., description="API source ID"),
    db: AsyncSession = Depends(get_db),
):
    """Delete an API source configuration."""
    service = ApiSourceService(db)

    try:
        uuid_id = UUID(source_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid source ID format")

    deleted = await service.delete(uuid_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="API source not found")
