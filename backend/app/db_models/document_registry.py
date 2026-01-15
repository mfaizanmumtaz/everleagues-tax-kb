"""Document Registry models - links PostgreSQL to Solr documents."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database.base import Base, UUIDMixin, TimestampMixin


class DocumentRegistry(Base, UUIDMixin, TimestampMixin):
    """Registry linking PostgreSQL metadata to Solr documents."""

    __tablename__ = "document_registry"

    # Solr reference
    solr_document_id = Column(String(100), unique=True, nullable=False, index=True)

    # Source tracking
    scrape_url_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scrape_urls.id", ondelete="SET NULL"),
        index=True,
    )
    uploaded_file_id = Column(
        UUID(as_uuid=True), ForeignKey("uploaded_files.id", ondelete="SET NULL")
    )
    scrape_job_id = Column(
        UUID(as_uuid=True), ForeignKey("scrape_jobs.id", ondelete="SET NULL")
    )

    # Quick reference (denormalized from Solr for fast queries)
    document_name = Column(String(255))
    title = Column(String(500))
    jurisdiction = Column(String(50), index=True)
    state = Column(String(50), index=True)
    city = Column(String(100), index=True)  # City name for local-level documents
    tax_year = Column(Integer, index=True)
    governance_state = Column(String(50), index=True)
    doc_type = Column(String(100))
    category = Column(String(100))

    # Source URL for reference
    source_url = Column(Text)

    # Versioning
    version = Column(Integer, default=1)
    is_latest = Column(Boolean, default=True, index=True)

    # Chunk count (denormalized)
    chunk_count = Column(Integer, default=0)

    # Relationships
    scrape_url = relationship("ScrapeUrl", back_populates="document_registries")
    scrape_job = relationship("ScrapeJob", back_populates="document_registries")
    blobs = relationship(
        "DocumentBlob", back_populates="document_registry", cascade="all, delete-orphan"
    )
    governance_transitions = relationship(
        "GovernanceTransition",
        back_populates="document_registry",
        cascade="all, delete-orphan",
    )


class DocumentBlob(Base, UUIDMixin):
    """Blob storage references for documents."""

    __tablename__ = "document_blobs"

    # Foreign key
    document_registry_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Blob identification
    blob_type = Column(String(50), nullable=False)  # raw, processed, chunk
    blob_container = Column(String(100), nullable=False)
    blob_path = Column(Text, nullable=False)
    blob_url = Column(Text)

    # File info
    file_size = Column(Integer)  # in bytes
    mime_type = Column(String(100))
    content_hash = Column(String(64), index=True)  # SHA-256 for deduplication

    # Versioning
    version = Column(Integer, default=1)
    is_current = Column(Boolean, default=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    # Relationships
    document_registry = relationship("DocumentRegistry", back_populates="blobs")
