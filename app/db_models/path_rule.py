"""Path Rule model for blocking/allowing scraping paths."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    Text,
    Enum,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from ..database.base import Base, UUIDMixin, TimestampMixin


class RuleType(str, enum.Enum):
    """Type of path rule."""

    BLOCK = "block"   # Blacklist - prevent scraping this path
    ALLOW = "allow"   # Whitelist - explicitly allow (can override robots.txt)


class RuleSource(str, enum.Enum):
    """Source of the rule."""

    MANUAL = "manual"       # User created manually
    ROBOTS_TXT = "robots_txt"  # Imported from robots.txt
    AUTO = "auto"           # System auto-detected (e.g., login pages)


class PathRule(Base, UUIDMixin, TimestampMixin):
    """
    Stores path rules for blocking or allowing specific URL paths.
    
    Rules can be exact matches or patterns (glob/regex).
    Used during discovery and scraping to filter out unwanted paths.
    """

    __tablename__ = "path_rules"

    # Foreign key to parent URL
    scrape_url_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scrape_urls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Rule definition
    pattern = Column(Text, nullable=False)  # e.g., "/login/*", "/cart", "*.pdf"
    rule_type = Column(
        Enum(RuleType, name="rule_type"),
        nullable=False,
        default=RuleType.BLOCK,
        index=True,
    )
    
    # Pattern matching options
    is_regex = Column(Boolean, default=False)  # If true, pattern is regex
    is_glob = Column(Boolean, default=True)    # If true, pattern is glob (default)
    case_sensitive = Column(Boolean, default=False)
    
    # Rule metadata
    reason = Column(Text)                      # Why this path is blocked/allowed
    source = Column(
        Enum(RuleSource, name="rule_source"),
        nullable=False,
        default=RuleSource.MANUAL,
    )
    
    # Priority (higher = evaluated first)
    priority = Column(Integer, default=0)
    
    # Statistics
    match_count = Column(Integer, default=0)   # How many times this rule matched
    
    # Relationships
    scrape_url = relationship("ScrapeUrl", back_populates="path_rules")
