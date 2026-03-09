"""Pydantic models for page discovery and path rule operations."""

from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


# ==================== Enums ====================


class PageStatusEnum(str, Enum):
    """Page status filter enum."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    INGESTED = "ingested"


class RuleTypeEnum(str, Enum):
    """Rule type enum."""

    BLOCK = "block"
    ALLOW = "allow"


class RuleSourceEnum(str, Enum):
    """Rule source enum."""

    MANUAL = "manual"
    ROBOTS_TXT = "robots_txt"
    AUTO = "auto"


# ==================== Discovery Models ====================


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
    queue_size: int = 0
    current_depth: int = 0
    recent_urls: List[dict] = Field(default_factory=list)
    rules_refreshed_count: int = 0
    urls_skipped_by_rules: int = 0


# ==================== Discovered Page Models ====================


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


# ==================== Path Rule Models ====================


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


# ==================== Site Tree Models ====================


class SiteTreeNode(BaseModel):
    """Site tree node."""

    path: str
    depth: int
    page_count: int
    pages: List[dict]
    children: List["SiteTreeNode"]


# Enable self-referencing
SiteTreeNode.model_rebuild()
