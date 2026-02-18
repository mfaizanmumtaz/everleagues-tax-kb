"""Discovered Page model for pre-ingestion review."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Enum,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from ..database.base import Base, UUIDMixin, TimestampMixin


class PageStatus(str, enum.Enum):
    """Status of a discovered page."""

    PENDING = "pending"      # Awaiting review
    APPROVED = "approved"    # Approved for ingestion
    REJECTED = "rejected"    # Rejected, won't be scraped
    INGESTED = "ingested"    # Already ingested into RAG


class DiscoveredPage(Base, UUIDMixin, TimestampMixin):
    """
    Stores pages discovered during the discovery phase.
    
    Pages are discovered by crawling a site before actual ingestion.
    Users can review, approve, or reject pages before they are scraped.
    """

    __tablename__ = "discovered_pages"

    # Foreign key to parent URL
    scrape_url_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scrape_urls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Page information
    url = Column(Text, nullable=False)
    path = Column(Text, nullable=False)  # Relative path, e.g., "/tax-forms/2024"
    depth = Column(Integer, default=0)    # URL depth level from base URL
    
    # Page metadata (discovered during crawl)
    title = Column(String(500))           # Page title if found
    content_type = Column(String(100))    # text/html, application/pdf, etc.
    content_length = Column(Integer)      # Size in bytes if known
    
    # Review status
    status = Column(
        Enum(PageStatus, name="page_status"),
        nullable=False,
        default=PageStatus.PENDING,
        index=True,
    )
    reviewed_at = Column(DateTime(timezone=True))
    reviewed_by = Column(String(100))     # User who reviewed
    rejection_reason = Column(Text)       # Reason if rejected
    
    # Discovery metadata
    discovered_at = Column(DateTime(timezone=True))
    discovery_job_id = Column(UUID(as_uuid=True))  # Which discovery job found this
    
    # Crawl info
    http_status = Column(Integer)         # HTTP status code when discovered
    is_document = Column(Boolean, default=False)  # If this is a downloadable doc
    parent_page_id = Column(
        UUID(as_uuid=True),
        ForeignKey("discovered_pages.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    scrape_url = relationship("ScrapeUrl", back_populates="discovered_pages")
    children = relationship(
        "DiscoveredPage",
        backref="parent_page",
        remote_side="DiscoveredPage.id",
        foreign_keys=[parent_page_id],
    )
