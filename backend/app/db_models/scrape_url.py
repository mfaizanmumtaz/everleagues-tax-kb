"""URL Management models for scraping sources."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Enum,
    LargeBinary,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from ..database.base import Base, UUIDMixin, TimestampMixin


class DataSourceType(str, enum.Enum):
    """Data source type enumeration."""

    SCRAPE = "scrape"
    API = "api"
    FILE = "file"


class ScheduleFrequency(str, enum.Enum):
    """Schedule frequency enumeration."""

    ON_DEMAND = "on_demand"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


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
    category = Column(
        String(50), nullable=False, default="Federal", index=True
    )  # Federal, State, Local
    state = Column(String(50), index=True)  # State name (California, New York, etc.)
    city = Column(String(100), index=True)  # City name for local-level documents
    jurisdiction = Column(String(50))  # federal, state, local

    # Data Source Configuration
    data_source = Column(
        Enum(DataSourceType, name="data_source_type"),
        nullable=False,
        default=DataSourceType.SCRAPE,
    )

    # Scheduling
    schedule_frequency = Column(
        Enum(ScheduleFrequency, name="schedule_frequency"),
        nullable=False,
        default=ScheduleFrequency.ON_DEMAND,
    )
    next_scheduled_run = Column(DateTime(timezone=True))

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
    api_credential = relationship(
        "ApiCredential",
        back_populates="scrape_url",
        uselist=False,
        cascade="all, delete-orphan",
    )
    scrape_jobs = relationship(
        "ScrapeJob", back_populates="scrape_url", cascade="all, delete-orphan"
    )
    document_registries = relationship("DocumentRegistry", back_populates="scrape_url")


class ApiCredential(Base, UUIDMixin, TimestampMixin):
    """API credentials for data_source = 'api'."""

    __tablename__ = "api_credentials"

    # Foreign key
    scrape_url_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scrape_urls.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # API Configuration
    api_endpoint = Column(Text, nullable=False)
    api_key_encrypted = Column(LargeBinary)  # Encrypted
    auth_type = Column(String(50), default="bearer")  # bearer, basic, api_key

    # Relationships
    scrape_url = relationship("ScrapeUrl", back_populates="api_credential")
