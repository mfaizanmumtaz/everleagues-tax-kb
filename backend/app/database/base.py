"""SQLAlchemy base classes and mixins."""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, text
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()


class UUIDMixin:
    """UUID primary key mixin."""
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )


class TimestampMixin:
    """Timestamp mixin for created_at and updated_at."""
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()")
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=datetime.utcnow
    )

