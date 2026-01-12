"""Audit log models - for Governance Audit Log feature."""

from sqlalchemy import Column, String, Integer, DateTime, Text, text
from sqlalchemy.dialects.postgresql import JSONB

from ..database.base import Base


class AuditLog(Base):
    """Audit log for system actions - shown in Governance Audit Log."""
    
    __tablename__ = "audit_logs"
    
    # Primary key (auto-increment for high-volume inserts)
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Actor (just strings, no user table for now)
    actor = Column(String(255))  # Who performed the action
    
    # Action
    action = Column(String(100), nullable=False, index=True)
    # Actions: document.create, document.update, document.delete, 
    #          governance.change, url.create, url.scrape, etc.
    
    resource_type = Column(String(50), nullable=False, index=True)
    # Resource types: document, chunk, url, etc.
    
    resource_id = Column(String(100), index=True)
    resource_name = Column(String(255))  # For display purposes
    
    # Details
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    details = Column(Text)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), index=True)

