"""URL Management models for scraping sources."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    Enum,
)
from sqlalchemy.orm import relationship
import enum

from ..database.base import Base, UUIDMixin, TimestampMixin


class DataSourceType(str, enum.Enum):
    """Data source type enumeration."""

    SCRAPE = "scrape"
    FILE = "file"


class UrlStatus(str, enum.Enum):
    """URL status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SCRAPING = "scraping"


class ScrapeUrl(Base, UUIDMixin, TimestampMixin):
    """Scraping URL configuration."""

    __tablename__ = "scrape_urls"

    # URL Information
    url = Column(Text, nullable=False, unique=True)
    name = Column(String(255))
    description = Column(Text)

    # Classification
    state = Column(String(50), index=True)  # State name (California, New York, etc.)
    city = Column(String(100), index=True)  # City name for local-level documents
    jurisdiction = Column(String(50), nullable=False, default="federal", index=True)  # federal, state, local

    # Data Source Configuration
    data_source = Column(
        Enum(DataSourceType, name="data_source_type"),
        nullable=False,
        default=DataSourceType.SCRAPE,
    )

    # Rate Limiting
    delay_between_requests = Column(Integer, default=2)  # seconds
    max_requests_per_minute = Column(Integer, default=30)
    max_files_per_session = Column(Integer, default=10000)

    # Status
    status = Column(
        Enum(UrlStatus, name="url_status"),
        nullable=False,
        default=UrlStatus.ACTIVE,
        index=True,
    )
    error_message = Column(Text)

    # Statistics
    documents_count = Column(Integer, default=0)
    last_scraped_at = Column(DateTime(timezone=True))
    last_successful_at = Column(DateTime(timezone=True))

    # Relationships
    scrape_jobs = relationship(
        "ScrapeJob", back_populates="scrape_url", cascade="all, delete-orphan"
    )
    document_registries = relationship("DocumentRegistry", back_populates="scrape_url")
    discovered_pages = relationship(
        "DiscoveredPage", back_populates="scrape_url", cascade="all, delete-orphan"
    )
    path_rules = relationship(
        "PathRule", back_populates="scrape_url", cascade="all, delete-orphan"
    )
