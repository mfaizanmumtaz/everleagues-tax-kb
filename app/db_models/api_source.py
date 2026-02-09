"""API Source Configuration models for external API data sources."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    Enum,
    LargeBinary,
    JSON,
)
import enum

from ..database.base import Base, UUIDMixin, TimestampMixin


class ApiSourceCategory(str, enum.Enum):
    """API source category enumeration."""

    FEDERAL = "federal"
    STATE = "state"
    LOCAL = "local"
    FORMS = "forms"


class ApiSourceStatus(str, enum.Enum):
    """API source status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"


class AuthType(str, enum.Enum):
    """Authentication type enumeration."""

    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    OAUTH = "oauth"
    NONE = "none"


class FetchFrequency(str, enum.Enum):
    """Fetch frequency enumeration."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ApiSource(Base, UUIDMixin, TimestampMixin):
    """External API source configuration."""

    __tablename__ = "api_sources"

    # Basic Information
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # API Configuration
    api_endpoint = Column(Text, nullable=False)

    # Classification
    category = Column(
        Enum(ApiSourceCategory, name="api_source_category"),
        nullable=False,
        default=ApiSourceCategory.FEDERAL,
    )

    # Status
    status = Column(
        Enum(ApiSourceStatus, name="api_source_status"),
        nullable=False,
        default=ApiSourceStatus.ACTIVE,
        index=True,
    )

    # Authentication
    auth_type = Column(
        Enum(AuthType, name="auth_type"),
        nullable=False,
        default=AuthType.API_KEY,
    )
    api_key_encrypted = Column(LargeBinary)
    oauth_token_encrypted = Column(LargeBinary)
    custom_headers = Column(JSON)

    # Scheduling
    fetch_frequency = Column(
        Enum(FetchFrequency, name="fetch_frequency"),
        nullable=False,
        default=FetchFrequency.DAILY,
    )

    # Limits
    max_file_size_mb = Column(Integer, default=50)

    # Tracking (updated by external service)
    last_fetched_at = Column(DateTime(timezone=True))
    total_files_pushed = Column(Integer, default=0)
    error_message = Column(Text)
