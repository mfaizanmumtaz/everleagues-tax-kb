"""SQLAlchemy database models - Simplified for current frontend features."""

from .scrape_url import ScrapeUrl, ApiCredential, UploadedFile
from .scrape_job import ScrapeJob, ScrapeJobLog
from .document_registry import DocumentRegistry, DocumentBlob
from .governance import GovernanceTransition
from .audit import AuditLog
from .system import SystemSetting

__all__ = [
    # URL Management
    "ScrapeUrl",
    "ApiCredential",
    "UploadedFile",
    # Scrape Jobs
    "ScrapeJob",
    "ScrapeJobLog",
    # Document Registry
    "DocumentRegistry",
    "DocumentBlob",
    # Governance
    "GovernanceTransition",
    # Audit
    "AuditLog",
    # System
    "SystemSetting",
]

