"""SQLAlchemy database models."""

from .scrape_url import ScrapeUrl, ApiCredential
from .scrape_job import ScrapeJob, ScrapeJobLog
from .document_registry import (
    DocumentRegistry,
    DocumentBlob,
    SourceType,
    ProcessingStatus,
)
from .governance import GovernanceTransition
from .audit import AuditLog
from .system import SystemSetting
from .discovered_page import DiscoveredPage, PageStatus
from .path_rule import PathRule, RuleType, RuleSource

__all__ = [
    # URL Management
    "ScrapeUrl",
    "ApiCredential",
    # Scrape Jobs
    "ScrapeJob",
    "ScrapeJobLog",
    # Document Registry
    "DocumentRegistry",
    "DocumentBlob",
    "SourceType",
    "ProcessingStatus",
    # Governance
    "GovernanceTransition",
    # Audit
    "AuditLog",
    # System
    "SystemSetting",
    # Discovery
    "DiscoveredPage",
    "PageStatus",
    # Path Rules
    "PathRule",
    "RuleType",
    "RuleSource",
]

