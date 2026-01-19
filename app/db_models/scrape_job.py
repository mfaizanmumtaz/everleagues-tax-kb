"""Scrape Job models for tracking scraping operations."""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from ..database.base import Base, UUIDMixin


class JobStatus(str, enum.Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScrapeJob(Base, UUIDMixin):
    """Scrape job for tracking scraping operations."""

    __tablename__ = "scrape_jobs"

    # Foreign key
    scrape_url_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scrape_urls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Job Status
    status = Column(
        Enum(JobStatus, name="job_status"),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    )

    # Progress
    progress_current = Column(Integer, default=0)
    progress_total = Column(Integer, default=0)
    progress_message = Column(Text)

    # Results
    documents_created = Column(Integer, default=0)
    documents_updated = Column(Integer, default=0)
    documents_failed = Column(Integer, default=0)
    chunks_created = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)

    # Error handling
    error_message = Column(Text)
    error_details = Column(JSONB)

    # Trigger info
    triggered_by = Column(String(50))  # scheduler, manual, api

    # Blob storage references
    raw_content_blob_path = Column(Text)
    processed_content_blob_path = Column(Text)

    # Timestamp
    created_at = Column(
        DateTime(timezone=True), server_default=text("now()"), index=True
    )

    # Relationships
    scrape_url = relationship("ScrapeUrl", back_populates="scrape_jobs")
    logs = relationship(
        "ScrapeJobLog", back_populates="job", cascade="all, delete-orphan"
    )
    document_registries = relationship("DocumentRegistry", back_populates="scrape_job")


class LogLevel(str, enum.Enum):
    """Log level enumeration."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ScrapeJobLog(Base):
    """Detailed logs for scrape jobs."""

    __tablename__ = "scrape_job_logs"

    # Primary key (auto-increment for performance)
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scrape_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Log content
    level = Column(Enum(LogLevel, name="log_level"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    details = Column(JSONB)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    # Relationships
    job = relationship("ScrapeJob", back_populates="logs")
