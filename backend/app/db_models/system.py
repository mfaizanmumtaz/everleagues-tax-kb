"""System configuration models."""

from sqlalchemy import Column, String, DateTime, Text, text
from sqlalchemy.dialects.postgresql import JSONB

from ..database.base import Base


class SystemSetting(Base):
    """System-wide configuration settings."""
    
    __tablename__ = "system_settings"
    
    # Primary key is the setting key
    key = Column(String(100), primary_key=True)
    
    # Value (stored as JSON for flexibility)
    value = Column(JSONB, nullable=False)
    
    # Metadata
    description = Column(Text)
    
    # Audit
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"))

