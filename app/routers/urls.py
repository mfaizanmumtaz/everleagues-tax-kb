"""URL Management API routes with PostgreSQL persistence."""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
import redis as redis_lib

from ..config import settings
from ..database.connection import get_db
from ..services.url_db_service import UrlDbService
from ..services.audit_log_service import AuditLogService
from ..services.scrape_job_service import ScrapeJobService
from ..db_models.scrape_job import JobStatus
from ..worker.tasks import process_scrape
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
    schedule_frequency: ScheduleFrequency = Field(
        default=ScheduleFrequency.ON_DEMAND, description="Scraping schedule"
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
    schedule_frequency: Optional[ScheduleFrequency] = None
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
    job_id: Optional[str] = None
    status: str = "idle"
    current: int = 0
    total: int = 0
    message: str = ""
    documents_created: int = 0
    documents_failed: int = 0
    started_at: Optional[str] = None


# ==================== Helper Functions ====================


def _map_data_source(api_value: DataSource) -> DbDataSourceType:
    """Map API data source to DB enum."""
    mapping = {
        DataSource.SCRAPE: DbDataSourceType.SCRAPE,
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


# Redis client for scrape cancellation
_redis_client: Optional[redis_lib.Redis] = None


def _get_redis() -> redis_lib.Redis:
    """Get or create a Redis client for cancellation signals."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.Redis.from_url(
            settings.celery_broker_url, decode_responses=True
        )
    return _redis_client


# ==================== API Endpoints ====================


@router.get("", response_model=URLListResponse)
async def list_urls(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    state: Optional[str] = Query(default=None, description="Filter by state"),
    status: Optional[URLStatus] = Query(default=None, description="Filter by status"),
    data_source: Optional[DataSource] = Query(
        default=None, description="Filter by data source"
    ),
    search: Optional[str] = Query(default=None, description="Search in URL"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    List URLs with filters and pagination.
    """
    try:
        url_service = UrlDbService(db)

        # Map status and data_source to DB enums if provided
        db_status = _map_url_status(status) if status else None
        db_data_source = _map_data_source(data_source) if data_source else None

        urls, total = await url_service.list_urls(
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
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single URL by ID.
    """
    try:
        url_service = UrlDbService(db)
        scrape_url = await url_service.get_url(UUID(url_id))

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
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new URL for scraping.
    """
    try:
        url_service = UrlDbService(db)
        audit_service = AuditLogService(db)

        # Check if URL already exists
        existing = await url_service.get_url_by_url(url_data.url)
        if existing:
            raise HTTPException(status_code=400, detail="URL already exists")

        scrape_url = await url_service.create_url(
            url=url_data.url,
            name=url_data.name,
            description=url_data.description,
            jurisdiction=url_data.category,  # Frontend sends 'category', backend stores as 'jurisdiction'
            state=url_data.state,
            city=url_data.city,
            data_source=_map_data_source(url_data.data_source),
            schedule_frequency=_map_schedule_frequency(url_data.schedule_frequency),
            delay_between_requests=url_data.delay_between_requests,
            max_requests_per_minute=url_data.max_requests_per_minute,
            max_files_per_session=url_data.max_files_per_session,
        )

        # Log the action
        await audit_service.log_url_create(
            url_id=str(scrape_url.id),
            url=scrape_url.url,
            values={
                "category": url_data.category,
                "data_source": url_data.data_source.value,
            },
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
    db: AsyncSession = Depends(get_db),
):
    """
    Update a URL.
    """
    try:
        url_service = UrlDbService(db)

        # Get existing URL for audit log (old values)
        existing = await url_service.get_url(UUID(url_id))
        if not existing:
            raise HTTPException(status_code=404, detail="URL not found")

        # Capture old values for audit log
        update_data = updates.model_dump(exclude_unset=True)
        old_values = {}
        for key in update_data:
            old_val = getattr(existing, key, None)
            if old_val is not None:
                old_values[key] = old_val.value if hasattr(old_val, "value") else old_val
            else:
                old_values[key] = None

        # Build update kwargs
        update_kwargs = {}

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

        scrape_url = await url_service.update_url(UUID(url_id), **update_kwargs)

        if not scrape_url:
            raise HTTPException(status_code=404, detail="URL not found")

        # Audit log: URL updated
        try:
            audit_service = AuditLogService(db)
            await audit_service.log_action(
                action="url.update",
                resource_type="url",
                resource_id=url_id,
                resource_name=existing.url,
                old_values=old_values,
                new_values=update_data,
                details=f"URL configuration updated: {', '.join(update_data.keys())}",
            )
        except Exception:
            pass  # Don't fail the request if audit logging fails

        return URLResponse(**url_service.to_dict(scrape_url))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{url_id}", status_code=204)
async def delete_url(
    url_id: str = Path(..., description="URL ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a URL.
    """
    try:
        url_service = UrlDbService(db)
        audit_service = AuditLogService(db)

        # Get URL for audit log
        scrape_url = await url_service.get_url(UUID(url_id))
        if not scrape_url:
            raise HTTPException(status_code=404, detail="URL not found")

        url_string = scrape_url.url

        # Delete
        if not await url_service.delete_url(UUID(url_id)):
            raise HTTPException(status_code=404, detail="URL not found")

        # Log the action
        await audit_service.log_url_delete(url_id=url_id, url=url_string)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{url_id}/scrape", response_model=ScrapeProgress)
async def trigger_scrape(
    url_id: str = Path(..., description="URL ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger scraping for a URL.

    Downloads all approved discovered pages and processes them through
    the full ingestion pipeline (blob, parse, classify, chunk, embed, Solr).
    The scrape is executed asynchronously via a Celery worker task.
    """
    try:
        url_service = UrlDbService(db)
        job_service = ScrapeJobService(db)

        scrape_url = await url_service.get_url(UUID(url_id))
        if not scrape_url:
            raise HTTPException(status_code=404, detail="URL not found")

        # Check if already scraping
        if scrape_url.status == DbUrlStatus.SCRAPING:
            # Return progress of the current job
            jobs, _ = await job_service.get_jobs_for_url(UUID(url_id), page=1, limit=1)
            if jobs and jobs[0].status.value == "running":
                job = jobs[0]
                return ScrapeProgress(
                    url_id=url_id,
                    job_id=str(job.id),
                    status="running",
                    current=job.progress_current or 0,
                    total=job.progress_total or 0,
                    message=job.progress_message or "Scraping in progress",
                    documents_created=job.documents_created or 0,
                    documents_failed=job.documents_failed or 0,
                    started_at=job.started_at.isoformat() if job.started_at else None,
                )

        # Create a new scrape job
        job = await job_service.create_job(UUID(url_id), triggered_by="manual")

        # Queue the scrape task via Celery
        process_scrape.delay(scrape_url_id=url_id, job_id=str(job.id))

        return ScrapeProgress(
            url_id=url_id,
            job_id=str(job.id),
            status="pending",
            current=0,
            total=0,
            message="Scrape job created, starting...",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{url_id}/scrape/progress", response_model=ScrapeProgress)
async def get_scrape_progress(
    url_id: str = Path(..., description="URL ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get scraping progress for a URL. Returns the latest job's progress.
    """
    try:
        url_service = UrlDbService(db)
        job_service = ScrapeJobService(db)

        scrape_url = await url_service.get_url(UUID(url_id))
        if not scrape_url:
            raise HTTPException(status_code=404, detail="URL not found")

        # Get the most recent job for this URL
        jobs, _ = await job_service.get_jobs_for_url(UUID(url_id), page=1, limit=1)

        if not jobs:
            return ScrapeProgress(
                url_id=url_id,
                status="idle",
                message="No scraping jobs found",
            )

        job = jobs[0]

        # Detect stale running jobs (Celery task crashed but never updated status)
        job_status = job.status.value if job.status else "idle"
        if job_status == "running" and job.started_at:
            elapsed = (datetime.now(timezone.utc) - job.started_at).total_seconds()
            if elapsed > settings.scrape_task_time_limit:
                # Job has been running longer than the hard time limit -- it's stale
                job_status = "failed"
                job.status = JobStatus.FAILED
                job.progress_message = "Job stopped unexpectedly"
                try:
                    await db.commit()
                except Exception:
                    pass

        return ScrapeProgress(
            url_id=url_id,
            job_id=str(job.id),
            status=job_status,
            current=job.progress_current or 0,
            total=job.progress_total or 0,
            message=job.progress_message or "",
            documents_created=job.documents_created or 0,
            documents_failed=job.documents_failed or 0,
            started_at=job.started_at.isoformat() if job.started_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{url_id}/scrape/cancel")
async def cancel_scrape(
    url_id: str = Path(..., description="URL ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel an active scrape for a URL.

    Sets a Redis cancellation key that the Celery worker checks on each
    loop iteration, then marks the job as cancelled in the database.
    """
    try:
        job_service = ScrapeJobService(db)
        jobs, _ = await job_service.get_jobs_for_url(UUID(url_id), page=1, limit=1)

        if jobs and jobs[0].status.value == "running":
            # Signal cancellation via Redis so the Celery worker stops
            redis_client = _get_redis()
            redis_client.setex(f"scrape:cancel:{url_id}", 3600, "1")
            await job_service.cancel_job(jobs[0].id)
            return {"message": "Cancellation signal sent", "url_id": url_id}

        return {"message": "No active scrape to cancel", "url_id": url_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
