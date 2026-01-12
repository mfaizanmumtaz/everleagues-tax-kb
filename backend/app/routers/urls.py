"""URL Management API routes with PostgreSQL persistence."""

from fastapi import APIRouter, HTTPException, Query, Path, BackgroundTasks, Depends
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..services.url_db_service import UrlDbService
from ..services.audit_log_service import AuditLogService
from ..db_models.scrape_url import (
    DataSourceType as DbDataSourceType,
    ScheduleFrequency as DbScheduleFrequency,
    UrlStatus as DbUrlStatus,
)

router = APIRouter(prefix="/urls", tags=["URL Management"])


# ==================== Pydantic Models ====================

class DataSource(str, Enum):
    """Data source type."""
    SCRAPE = "scrape"
    API = "api"
    FILE = "file"


class ScheduleFrequency(str, Enum):
    """Scraping schedule frequency."""
    ON_DEMAND = "on_demand"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class URLStatus(str, Enum):
    """URL status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SCRAPING = "scraping"


class URLBase(BaseModel):
    """Base URL fields."""
    url: str = Field(..., description="URL to scrape")
    category: str = Field(default="Federal", description="Category (Federal/State/Local)")
    state: Optional[str] = Field(default=None, description="State code if state-level or local-level")
    city: Optional[str] = Field(default=None, description="City name if local-level")
    data_source: DataSource = Field(default=DataSource.SCRAPE, description="Data source type")
    schedule_frequency: ScheduleFrequency = Field(default=ScheduleFrequency.ON_DEMAND, description="Scraping schedule")
    api_key: Optional[str] = Field(default=None, description="API key if data source is API")
    api_endpoint: Optional[str] = Field(default=None, description="API endpoint if data source is API")


class URLCreate(URLBase):
    """Request to create a URL."""
    name: Optional[str] = Field(default=None, description="Display name")
    description: Optional[str] = Field(default=None, description="Description")
    delay_between_requests: int = Field(default=2, ge=1, description="Seconds between requests")
    max_requests_per_minute: int = Field(default=30, ge=1, description="Max requests per minute")
    max_files_per_session: int = Field(default=10000, ge=1, description="Max files to download")


class URLUpdate(BaseModel):
    """Request to update a URL."""
    url: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    data_source: Optional[DataSource] = None
    schedule_frequency: Optional[ScheduleFrequency] = None
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
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
    schedule_frequency: str = "on_demand"
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
    status: str
    current: int = 0
    total: int = 0
    message: str = ""


# ==================== Helper Functions ====================

def _map_data_source(api_value: DataSource) -> DbDataSourceType:
    """Map API data source to DB enum."""
    mapping = {
        DataSource.SCRAPE: DbDataSourceType.SCRAPE,
        DataSource.API: DbDataSourceType.API,
        DataSource.FILE: DbDataSourceType.FILE,
    }
    return mapping.get(api_value, DbDataSourceType.SCRAPE)


def _map_schedule_frequency(api_value: ScheduleFrequency) -> DbScheduleFrequency:
    """Map API schedule frequency to DB enum."""
    mapping = {
        ScheduleFrequency.ON_DEMAND: DbScheduleFrequency.ON_DEMAND,
        ScheduleFrequency.DAILY: DbScheduleFrequency.DAILY,
        ScheduleFrequency.WEEKLY: DbScheduleFrequency.WEEKLY,
        ScheduleFrequency.MONTHLY: DbScheduleFrequency.MONTHLY,
        ScheduleFrequency.QUARTERLY: DbScheduleFrequency.QUARTERLY,
        ScheduleFrequency.YEARLY: DbScheduleFrequency.YEARLY,
    }
    return mapping.get(api_value, DbScheduleFrequency.ON_DEMAND)


def _map_url_status(api_value: URLStatus) -> DbUrlStatus:
    """Map API URL status to DB enum."""
    mapping = {
        URLStatus.ACTIVE: DbUrlStatus.ACTIVE,
        URLStatus.INACTIVE: DbUrlStatus.INACTIVE,
        URLStatus.ERROR: DbUrlStatus.ERROR,
        URLStatus.SCRAPING: DbUrlStatus.SCRAPING,
    }
    return mapping.get(api_value, DbUrlStatus.ACTIVE)


# In-memory storage for scrape progress (temporary until we implement job tracking)
_scrape_tasks: dict = {}


# ==================== API Endpoints ====================

@router.get("", response_model=URLListResponse)
async def list_urls(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    state: Optional[str] = Query(default=None, description="Filter by state"),
    status: Optional[URLStatus] = Query(default=None, description="Filter by status"),
    data_source: Optional[DataSource] = Query(default=None, description="Filter by data source"),
    search: Optional[str] = Query(default=None, description="Search in URL"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """
    List URLs with filters and pagination.
    """
    try:
        url_service = UrlDbService(db)
        
        # Map status and data_source to DB enums if provided
        db_status = _map_url_status(status) if status else None
        db_data_source = _map_data_source(data_source) if data_source else None
        
        urls, total = url_service.list_urls(
            category=category,
            state=state,
            status=db_status,
            data_source=db_data_source,
            search=search,
            page=page,
            limit=limit,
        )
        
        pages = (total + limit - 1) // limit if total > 0 else 1
        
        items = [URLResponse(**url_service.to_dict(u)) for u in urls]
        
        return URLListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{url_id}", response_model=URLResponse)
async def get_url(
    url_id: str = Path(..., description="URL ID"),
    db: Session = Depends(get_db),
):
    """
    Get a single URL by ID.
    """
    try:
        url_service = UrlDbService(db)
        scrape_url = url_service.get_url(UUID(url_id))
        
        if not scrape_url:
            raise HTTPException(status_code=404, detail="URL not found")
        
        return URLResponse(**url_service.to_dict(scrape_url))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=URLResponse, status_code=201)
async def create_url(
    url_data: URLCreate,
    db: Session = Depends(get_db),
):
    """
    Add a new URL for scraping.
    """
    try:
        url_service = UrlDbService(db)
        audit_service = AuditLogService(db)
        
        # Check if URL already exists
        existing = url_service.get_url_by_url(url_data.url)
        if existing:
            raise HTTPException(status_code=400, detail="URL already exists")
        
        scrape_url = url_service.create_url(
            url=url_data.url,
            name=url_data.name,
            description=url_data.description,
            category=url_data.category,
            state=url_data.state,
            city=url_data.city,
            data_source=_map_data_source(url_data.data_source),
            schedule_frequency=_map_schedule_frequency(url_data.schedule_frequency),
            api_endpoint=url_data.api_endpoint,
            api_key=url_data.api_key,
            delay_between_requests=url_data.delay_between_requests,
            max_requests_per_minute=url_data.max_requests_per_minute,
            max_files_per_session=url_data.max_files_per_session,
        )
        
        # Log the action
        audit_service.log_url_create(
            url_id=str(scrape_url.id),
            url=scrape_url.url,
            values={"category": url_data.category, "data_source": url_data.data_source.value},
        )
        
        return URLResponse(**url_service.to_dict(scrape_url))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{url_id}", response_model=URLResponse)
async def update_url(
    url_id: str = Path(..., description="URL ID"),
    updates: URLUpdate = ...,
    db: Session = Depends(get_db),
):
    """
    Update a URL.
    """
    try:
        url_service = UrlDbService(db)
        
        # Build update kwargs
        update_kwargs = {}
        update_data = updates.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            if value is not None:
                if key == "data_source":
                    update_kwargs["data_source"] = _map_data_source(value)
                elif key == "schedule_frequency":
                    update_kwargs["schedule_frequency"] = _map_schedule_frequency(value)
                elif key == "status":
                    update_kwargs["status"] = _map_url_status(value)
                else:
                    update_kwargs[key] = value
        
        scrape_url = url_service.update_url(UUID(url_id), **update_kwargs)
        
        if not scrape_url:
            raise HTTPException(status_code=404, detail="URL not found")
        
        return URLResponse(**url_service.to_dict(scrape_url))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{url_id}", status_code=204)
async def delete_url(
    url_id: str = Path(..., description="URL ID"),
    db: Session = Depends(get_db),
):
    """
    Delete a URL.
    """
    try:
        url_service = UrlDbService(db)
        audit_service = AuditLogService(db)
        
        # Get URL for audit log
        scrape_url = url_service.get_url(UUID(url_id))
        if not scrape_url:
            raise HTTPException(status_code=404, detail="URL not found")
        
        url_string = scrape_url.url
        
        # Delete
        if not url_service.delete_url(UUID(url_id)):
            raise HTTPException(status_code=404, detail="URL not found")
        
        # Log the action
        audit_service.log_url_delete(url_id=url_id, url=url_string)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{url_id}/scrape", response_model=ScrapeProgress)
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    url_id: str = Path(..., description="URL ID"),
    db: Session = Depends(get_db),
):
    """
    Trigger scraping for a URL.
    
    Starts a background task to scrape the URL.
    """
    try:
        url_service = UrlDbService(db)
        
        scrape_url = url_service.get_url(UUID(url_id))
        if not scrape_url:
            raise HTTPException(status_code=404, detail="URL not found")
        
        # Check if already scraping
        if scrape_url.status == DbUrlStatus.SCRAPING:
            return ScrapeProgress(
                url_id=url_id,
                status="scraping",
                current=_scrape_tasks.get(url_id, {}).get("current", 0),
                total=_scrape_tasks.get(url_id, {}).get("total", 0),
                message="Scraping already in progress",
            )
        
        # Update status to scraping
        url_service.update_url_status(UUID(url_id), DbUrlStatus.SCRAPING)
        
        # Initialize progress
        _scrape_tasks[url_id] = {
            "status": "started",
            "current": 0,
            "total": 0,
            "message": "Starting scrape...",
        }
        
        # Background task for scraping (mock implementation)
        async def do_scrape(uid: str, url_string: str):
            import asyncio
            from ..database.connection import SessionLocal
            
            try:
                _scrape_tasks[uid]["message"] = "Scanning URL..."
                _scrape_tasks[uid]["total"] = 10
                
                for i in range(10):
                    await asyncio.sleep(0.5)
                    _scrape_tasks[uid]["current"] = i + 1
                    _scrape_tasks[uid]["message"] = f"Processing document {i + 1}/10"
                
                _scrape_tasks[uid]["status"] = "completed"
                _scrape_tasks[uid]["message"] = "Scraping completed"
                
                # Update database with new session
                with SessionLocal() as db_session:
                    svc = UrlDbService(db_session)
                    audit_svc = AuditLogService(db_session)
                    
                    svc.update_url_status(UUID(uid), DbUrlStatus.ACTIVE)
                    svc.update_scrape_stats(
                        UUID(uid),
                        last_scraped_at=datetime.utcnow(),
                        last_successful_at=datetime.utcnow(),
                    )
                    svc.increment_documents_count(UUID(uid), 10)
                    
                    # Log the scrape action
                    audit_svc.log_url_scrape(
                        url_id=uid,
                        url=url_string,
                        documents_created=10,
                    )
                    
            except Exception as e:
                _scrape_tasks[uid]["status"] = "error"
                _scrape_tasks[uid]["message"] = str(e)
                
                # Update database with error status
                with SessionLocal() as db_session:
                    svc = UrlDbService(db_session)
                    svc.update_url_status(UUID(uid), DbUrlStatus.ERROR, str(e))
        
        background_tasks.add_task(do_scrape, url_id, scrape_url.url)
        
        return ScrapeProgress(
            url_id=url_id,
            status="started",
            current=0,
            total=0,
            message="Scraping started",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{url_id}/scrape/progress", response_model=ScrapeProgress)
async def get_scrape_progress(
    url_id: str = Path(..., description="URL ID"),
    db: Session = Depends(get_db),
):
    """
    Get scraping progress for a URL.
    """
    try:
        url_service = UrlDbService(db)
        
        scrape_url = url_service.get_url(UUID(url_id))
        if not scrape_url:
            raise HTTPException(status_code=404, detail="URL not found")
        
        progress = _scrape_tasks.get(url_id, {
            "status": "idle",
            "current": 0,
            "total": 0,
            "message": "No active scraping task",
        })
        
        return ScrapeProgress(
            url_id=url_id,
            status=progress.get("status", "idle"),
            current=progress.get("current", 0),
            total=progress.get("total", 0),
            message=progress.get("message", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
