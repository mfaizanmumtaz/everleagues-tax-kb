"""URL Management API routes."""

from fastapi import APIRouter, HTTPException, Query, Path, BackgroundTasks
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum

router = APIRouter(prefix="/urls", tags=["URL Management"])


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
    category: str = Field(default="Federal", description="Category (Federal/State)")
    state: Optional[str] = Field(default=None, description="State code if state-level")
    data_source: DataSource = Field(default=DataSource.SCRAPE, description="Data source type")
    schedule_frequency: ScheduleFrequency = Field(default=ScheduleFrequency.ON_DEMAND, description="Scraping schedule")
    api_key: Optional[str] = Field(default=None, description="API key if data source is API")
    api_endpoint: Optional[str] = Field(default=None, description="API endpoint if data source is API")


class URLCreate(URLBase):
    """Request to create a URL."""
    pass


class URLUpdate(BaseModel):
    """Request to update a URL."""
    url: Optional[str] = None
    category: Optional[str] = None
    state: Optional[str] = None
    data_source: Optional[DataSource] = None
    schedule_frequency: Optional[ScheduleFrequency] = None
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    status: Optional[URLStatus] = None


class URLResponse(URLBase):
    """URL response."""
    id: str
    status: URLStatus = URLStatus.ACTIVE
    last_scraped: Optional[datetime] = None
    documents_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


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


# In-memory storage for URLs (in production, use a database)
_urls_store: dict = {}
_scrape_tasks: dict = {}


def _generate_id() -> str:
    """Generate a unique ID."""
    import uuid
    return str(uuid.uuid4())


@router.get("", response_model=URLListResponse)
async def list_urls(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    state: Optional[str] = Query(default=None, description="Filter by state"),
    status: Optional[URLStatus] = Query(default=None, description="Filter by status"),
    data_source: Optional[DataSource] = Query(default=None, description="Filter by data source"),
    search: Optional[str] = Query(default=None, description="Search in URL"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    """
    List URLs with filters and pagination.
    """
    try:
        urls = list(_urls_store.values())
        
        # Apply filters
        if category:
            urls = [u for u in urls if u.get("category") == category]
        if state:
            urls = [u for u in urls if u.get("state") == state]
        if status:
            urls = [u for u in urls if u.get("status") == status.value]
        if data_source:
            urls = [u for u in urls if u.get("data_source") == data_source.value]
        if search:
            urls = [u for u in urls if search.lower() in u.get("url", "").lower()]
        
        # Sort by created_at descending
        urls.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        total = len(urls)
        pages = (total + limit - 1) // limit
        
        # Paginate
        start = (page - 1) * limit
        end = start + limit
        paginated = urls[start:end]
        
        # Convert to response
        items = [URLResponse(**u) for u in paginated]
        
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
):
    """
    Get a single URL by ID.
    """
    if url_id not in _urls_store:
        raise HTTPException(status_code=404, detail="URL not found")
    
    return URLResponse(**_urls_store[url_id])


@router.post("", response_model=URLResponse, status_code=201)
async def create_url(url_data: URLCreate):
    """
    Add a new URL for scraping.
    """
    try:
        now = datetime.utcnow()
        url_id = _generate_id()
        
        url_entry = {
            "id": url_id,
            "url": url_data.url,
            "category": url_data.category,
            "state": url_data.state,
            "data_source": url_data.data_source.value,
            "schedule_frequency": url_data.schedule_frequency.value,
            "api_key": url_data.api_key,
            "api_endpoint": url_data.api_endpoint,
            "status": URLStatus.ACTIVE.value,
            "last_scraped": None,
            "documents_count": 0,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }
        
        _urls_store[url_id] = url_entry
        
        return URLResponse(**url_entry)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{url_id}", response_model=URLResponse)
async def update_url(
    url_id: str = Path(..., description="URL ID"),
    updates: URLUpdate = ...,
):
    """
    Update a URL.
    """
    if url_id not in _urls_store:
        raise HTTPException(status_code=404, detail="URL not found")
    
    try:
        url_entry = _urls_store[url_id]
        
        update_data = updates.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                if hasattr(value, "value"):
                    value = value.value
                url_entry[key] = value
        
        url_entry["updated_at"] = datetime.utcnow()
        
        _urls_store[url_id] = url_entry
        
        return URLResponse(**url_entry)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{url_id}", status_code=204)
async def delete_url(
    url_id: str = Path(..., description="URL ID"),
):
    """
    Delete a URL.
    """
    if url_id not in _urls_store:
        raise HTTPException(status_code=404, detail="URL not found")
    
    del _urls_store[url_id]


@router.post("/{url_id}/scrape", response_model=ScrapeProgress)
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    url_id: str = Path(..., description="URL ID"),
):
    """
    Trigger scraping for a URL.
    
    Starts a background task to scrape the URL.
    """
    if url_id not in _urls_store:
        raise HTTPException(status_code=404, detail="URL not found")
    
    url_entry = _urls_store[url_id]
    
    # Check if already scraping
    if url_entry.get("status") == URLStatus.SCRAPING.value:
        return ScrapeProgress(
            url_id=url_id,
            status="scraping",
            current=_scrape_tasks.get(url_id, {}).get("current", 0),
            total=_scrape_tasks.get(url_id, {}).get("total", 0),
            message="Scraping already in progress",
        )
    
    # Update status
    url_entry["status"] = URLStatus.SCRAPING.value
    url_entry["updated_at"] = datetime.utcnow()
    _urls_store[url_id] = url_entry
    
    # Initialize progress
    _scrape_tasks[url_id] = {
        "status": "started",
        "current": 0,
        "total": 0,
        "message": "Starting scrape...",
    }
    
    # Add background task (mock implementation)
    async def mock_scrape(uid: str):
        import asyncio
        try:
            _scrape_tasks[uid]["message"] = "Scanning URL..."
            _scrape_tasks[uid]["total"] = 10
            
            for i in range(10):
                await asyncio.sleep(0.5)
                _scrape_tasks[uid]["current"] = i + 1
                _scrape_tasks[uid]["message"] = f"Processing document {i + 1}/10"
            
            _scrape_tasks[uid]["status"] = "completed"
            _scrape_tasks[uid]["message"] = "Scraping completed"
            
            # Update URL entry
            if uid in _urls_store:
                _urls_store[uid]["status"] = URLStatus.ACTIVE.value
                _urls_store[uid]["last_scraped"] = datetime.utcnow()
                _urls_store[uid]["documents_count"] += 10
                _urls_store[uid]["updated_at"] = datetime.utcnow()
                
        except Exception as e:
            _scrape_tasks[uid]["status"] = "error"
            _scrape_tasks[uid]["message"] = str(e)
            
            if uid in _urls_store:
                _urls_store[uid]["status"] = URLStatus.ERROR.value
                _urls_store[uid]["error_message"] = str(e)
                _urls_store[uid]["updated_at"] = datetime.utcnow()
    
    background_tasks.add_task(mock_scrape, url_id)
    
    return ScrapeProgress(
        url_id=url_id,
        status="started",
        current=0,
        total=0,
        message="Scraping started",
    )


@router.get("/{url_id}/scrape/progress", response_model=ScrapeProgress)
async def get_scrape_progress(
    url_id: str = Path(..., description="URL ID"),
):
    """
    Get scraping progress for a URL.
    """
    if url_id not in _urls_store:
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

