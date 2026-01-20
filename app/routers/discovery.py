"""Discovery API routes for page discovery and path management."""

from fastapi import APIRouter, HTTPException, Query, Path, BackgroundTasks, Depends
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db
from ..services.discovery_service import DiscoveryService
from ..services.discovered_page_service import DiscoveredPageService
from ..services.path_rule_service import PathRuleService
from ..services.url_db_service import UrlDbService
from ..db_models.discovered_page import PageStatus
from ..db_models.path_rule import RuleType, RuleSource

router = APIRouter(prefix="/urls", tags=["Discovery"])


# ==================== Pydantic Models ====================


class DiscoveryRequest(BaseModel):
    """Request to start page discovery."""

    max_depth: int = Field(default=3, ge=1, le=10, description="Maximum crawl depth")
    max_pages: int = Field(default=500, ge=1, le=5000, description="Maximum pages to discover")
    respect_robots: bool = Field(default=True, description="Respect robots.txt")
    delay_seconds: float = Field(default=1.0, ge=0.1, le=10.0, description="Delay between requests")
    add_common_blocks: bool = Field(default=True, description="Add common block patterns")


class DiscoveryStatusResponse(BaseModel):
    """Discovery status response."""

    url_id: str
    status: str
    pages_discovered: int = 0
    message: str = ""


class PageStatusEnum(str, Enum):
    """Page status filter enum."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    INGESTED = "ingested"


class DiscoveredPageResponse(BaseModel):
    """Discovered page response."""

    id: str
    url: str
    path: str
    depth: int
    title: Optional[str] = None
    content_type: Optional[str] = None
    status: str
    is_document: bool = False
    http_status: Optional[int] = None
    discovered_at: Optional[str] = None


class DiscoveredPageListResponse(BaseModel):
    """Response for discovered pages list."""

    items: List[DiscoveredPageResponse]
    total: int
    page: int
    limit: int
    pages: int


class PageApprovalRequest(BaseModel):
    """Request to approve/reject pages."""

    page_ids: List[str] = Field(..., description="List of page IDs")
    reason: Optional[str] = Field(default=None, description="Reason (for rejection)")


class BulkApprovalResponse(BaseModel):
    """Response for bulk approval/rejection."""

    affected_count: int
    message: str


class RuleTypeEnum(str, Enum):
    """Rule type enum."""

    BLOCK = "block"
    ALLOW = "allow"


class RuleSourceEnum(str, Enum):
    """Rule source enum."""

    MANUAL = "manual"
    ROBOTS_TXT = "robots_txt"
    AUTO = "auto"


class PathRuleCreate(BaseModel):
    """Request to create a path rule."""

    pattern: str = Field(..., description="Path pattern")
    rule_type: RuleTypeEnum = Field(default=RuleTypeEnum.BLOCK)
    reason: Optional[str] = None
    is_regex: bool = False
    is_glob: bool = True
    case_sensitive: bool = False
    priority: int = 0


class PathRuleResponse(BaseModel):
    """Path rule response."""

    id: str
    pattern: str
    rule_type: str
    reason: Optional[str] = None
    is_regex: bool = False
    is_glob: bool = True
    case_sensitive: bool = False
    priority: int = 0
    source: str
    match_count: int = 0
    created_at: Optional[str] = None


class PathRuleListResponse(BaseModel):
    """Response for path rules list."""

    items: List[PathRuleResponse]
    total: int


class SiteTreeNode(BaseModel):
    """Site tree node."""

    path: str
    depth: int
    page_count: int
    pages: List[dict]
    children: List["SiteTreeNode"]


# Enable self-referencing
SiteTreeNode.model_rebuild()


# ==================== In-Memory Discovery Status ====================

_discovery_status: dict = {}


# ==================== Discovery Endpoints ====================


@router.post("/{url_id}/discover", response_model=DiscoveryStatusResponse)
async def start_discovery(
    background_tasks: BackgroundTasks,
    url_id: str = Path(..., description="URL ID"),
    request: DiscoveryRequest = DiscoveryRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Start page discovery for a URL.
    
    Crawls the website to discover pages without ingesting content.
    Pages can then be reviewed and approved before actual scraping.
    """
    try:
        url_service = UrlDbService(db)
        scrape_url = await url_service.get_url(UUID(url_id))
        
        if not scrape_url:
            raise HTTPException(status_code=404, detail="URL not found")
        
        # Check if already discovering
        if url_id in _discovery_status and _discovery_status[url_id]["status"] == "running":
            return DiscoveryStatusResponse(
                url_id=url_id,
                status="running",
                pages_discovered=_discovery_status[url_id].get("pages", 0),
                message="Discovery already in progress",
            )
        
        # Initialize status
        _discovery_status[url_id] = {
            "status": "running",
            "pages": 0,
            "message": "Starting discovery...",
        }
        
        # Background discovery task
        async def run_discovery():
            from ..database.connection import AsyncSessionLocal
            
            async with AsyncSessionLocal() as session:
                try:
                    discovery_service = DiscoveryService(session)
                    path_rule_service = PathRuleService(session)
                    
                    # Add common blocks if requested
                    if request.add_common_blocks:
                        await path_rule_service.add_common_blocks(UUID(url_id))
                    
                    # Get path rules
                    rules = await path_rule_service.get_all_rules(UUID(url_id))
                    
                    _discovery_status[url_id]["message"] = "Crawling website..."
                    
                    # Run discovery
                    pages = await discovery_service.discover_pages(
                        scrape_url_id=UUID(url_id),
                        base_url=scrape_url.url,
                        max_depth=request.max_depth,
                        max_pages=request.max_pages,
                        respect_robots=request.respect_robots,
                        delay_seconds=request.delay_seconds,
                        path_rules=rules,
                    )
                    
                    _discovery_status[url_id] = {
                        "status": "completed",
                        "pages": len(pages),
                        "message": f"Discovered {len(pages)} pages",
                    }
                    
                    await discovery_service.close()
                    
                except Exception as e:
                    _discovery_status[url_id] = {
                        "status": "error",
                        "pages": 0,
                        "message": str(e),
                    }
        
        background_tasks.add_task(run_discovery)
        
        return DiscoveryStatusResponse(
            url_id=url_id,
            status="started",
            pages_discovered=0,
            message="Discovery started",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{url_id}/discover/status", response_model=DiscoveryStatusResponse)
async def get_discovery_status(
    url_id: str = Path(..., description="URL ID"),
):
    """Get the current discovery status for a URL."""
    status = _discovery_status.get(url_id, {
        "status": "idle",
        "pages": 0,
        "message": "No discovery running",
    })
    
    return DiscoveryStatusResponse(
        url_id=url_id,
        status=status["status"],
        pages_discovered=status["pages"],
        message=status["message"],
    )


@router.get("/{url_id}/discovered-pages", response_model=DiscoveredPageListResponse)
async def list_discovered_pages(
    url_id: str = Path(..., description="URL ID"),
    status: Optional[PageStatusEnum] = Query(default=None, description="Filter by status"),
    is_document: Optional[bool] = Query(default=None, description="Filter documents only"),
    min_depth: Optional[int] = Query(default=None, ge=0, description="Minimum depth"),
    max_depth: Optional[int] = Query(default=None, ge=0, description="Maximum depth"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """List discovered pages with filters and pagination."""
    try:
        page_service = DiscoveredPageService(db)
        
        # Map status enum
        page_status = None
        if status:
            page_status = PageStatus(status.value)
        
        pages, total = await page_service.list_pages(
            scrape_url_id=UUID(url_id),
            status=page_status,
            is_document=is_document,
            min_depth=min_depth,
            max_depth=max_depth,
            page=page,
            limit=limit,
        )
        
        total_pages = (total + limit - 1) // limit if total > 0 else 1
        
        items = [
            DiscoveredPageResponse(
                id=str(p.id),
                url=p.url,
                path=p.path,
                depth=p.depth,
                title=p.title,
                content_type=p.content_type,
                status=p.status.value,
                is_document=p.is_document or False,
                http_status=p.http_status,
                discovered_at=p.discovered_at.isoformat() if p.discovered_at else None,
            )
            for p in pages
        ]
        
        return DiscoveredPageListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=total_pages,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{url_id}/discovered-pages/approve", response_model=BulkApprovalResponse)
async def approve_pages(
    url_id: str = Path(..., description="URL ID"),
    request: PageApprovalRequest = ...,
    db: AsyncSession = Depends(get_db),
):
    """Approve selected pages for ingestion."""
    try:
        page_service = DiscoveredPageService(db)
        page_ids = [UUID(pid) for pid in request.page_ids]
        
        count = await page_service.approve_pages(page_ids)
        
        return BulkApprovalResponse(
            affected_count=count,
            message=f"Approved {count} pages",
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{url_id}/discovered-pages/reject", response_model=BulkApprovalResponse)
async def reject_pages(
    url_id: str = Path(..., description="URL ID"),
    request: PageApprovalRequest = ...,
    db: AsyncSession = Depends(get_db),
):
    """Reject selected pages (won't be ingested)."""
    try:
        page_service = DiscoveredPageService(db)
        page_ids = [UUID(pid) for pid in request.page_ids]
        
        count = await page_service.reject_pages(page_ids, reason=request.reason)
        
        return BulkApprovalResponse(
            affected_count=count,
            message=f"Rejected {count} pages",
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{url_id}/discovered-pages/approve-all", response_model=BulkApprovalResponse)
async def approve_all_pages(
    url_id: str = Path(..., description="URL ID"),
    db: AsyncSession = Depends(get_db),
):
    """Approve all pending pages."""
    try:
        page_service = DiscoveredPageService(db)
        count = await page_service.approve_all_pending(UUID(url_id))
        
        return BulkApprovalResponse(
            affected_count=count,
            message=f"Approved {count} pages",
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{url_id}/discovered-pages/reject-all", response_model=BulkApprovalResponse)
async def reject_all_pages(
    url_id: str = Path(..., description="URL ID"),
    reason: Optional[str] = Query(default=None, description="Rejection reason"),
    db: AsyncSession = Depends(get_db),
):
    """Reject all pending pages."""
    try:
        page_service = DiscoveredPageService(db)
        count = await page_service.reject_all_pending(UUID(url_id), reason=reason)
        
        return BulkApprovalResponse(
            affected_count=count,
            message=f"Rejected {count} pages",
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{url_id}/site-tree", response_model=SiteTreeNode)
async def get_site_tree(
    url_id: str = Path(..., description="URL ID"),
    db: AsyncSession = Depends(get_db),
):
    """Get hierarchical site structure of discovered pages."""
    try:
        discovery_service = DiscoveryService(db)
        tree = await discovery_service.build_site_tree(UUID(url_id))
        return tree
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{url_id}/discovery-stats")
async def get_discovery_stats(
    url_id: str = Path(..., description="URL ID"),
    db: AsyncSession = Depends(get_db),
):
    """Get statistics about discovered pages."""
    try:
        discovery_service = DiscoveryService(db)
        stats = await discovery_service.get_discovery_stats(UUID(url_id))
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Path Rules Endpoints ====================


@router.get("/{url_id}/path-rules", response_model=PathRuleListResponse)
async def list_path_rules(
    url_id: str = Path(..., description="URL ID"),
    rule_type: Optional[RuleTypeEnum] = Query(default=None, description="Filter by type"),
    source: Optional[RuleSourceEnum] = Query(default=None, description="Filter by source"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List path rules for a URL."""
    try:
        rule_service = PathRuleService(db)
        
        # Map enums
        db_rule_type = RuleType(rule_type.value) if rule_type else None
        db_source = RuleSource(source.value) if source else None
        
        rules, total = await rule_service.list_rules(
            scrape_url_id=UUID(url_id),
            rule_type=db_rule_type,
            source=db_source,
            page=page,
            limit=limit,
        )
        
        items = [
            PathRuleResponse(
                id=str(r.id),
                pattern=r.pattern,
                rule_type=r.rule_type.value,
                reason=r.reason,
                is_regex=r.is_regex,
                is_glob=r.is_glob,
                case_sensitive=r.case_sensitive,
                priority=r.priority,
                source=r.source.value,
                match_count=r.match_count or 0,
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
            for r in rules
        ]
        
        return PathRuleListResponse(items=items, total=total)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{url_id}/path-rules", response_model=PathRuleResponse, status_code=201)
async def create_path_rule(
    url_id: str = Path(..., description="URL ID"),
    request: PathRuleCreate = ...,
    db: AsyncSession = Depends(get_db),
):
    """Create a new path rule."""
    try:
        rule_service = PathRuleService(db)
        
        rule = await rule_service.create_rule(
            scrape_url_id=UUID(url_id),
            pattern=request.pattern,
            rule_type=RuleType(request.rule_type.value),
            reason=request.reason,
            is_regex=request.is_regex,
            is_glob=request.is_glob,
            case_sensitive=request.case_sensitive,
            priority=request.priority,
        )
        
        return PathRuleResponse(
            id=str(rule.id),
            pattern=rule.pattern,
            rule_type=rule.rule_type.value,
            reason=rule.reason,
            is_regex=rule.is_regex,
            is_glob=rule.is_glob,
            case_sensitive=rule.case_sensitive,
            priority=rule.priority,
            source=rule.source.value,
            match_count=rule.match_count or 0,
            created_at=rule.created_at.isoformat() if rule.created_at else None,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{url_id}/path-rules/{rule_id}", status_code=204)
async def delete_path_rule(
    url_id: str = Path(..., description="URL ID"),
    rule_id: str = Path(..., description="Rule ID"),
    db: AsyncSession = Depends(get_db),
):
    """Delete a path rule."""
    try:
        rule_service = PathRuleService(db)
        
        if not await rule_service.delete_rule(UUID(rule_id)):
            raise HTTPException(status_code=404, detail="Rule not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
