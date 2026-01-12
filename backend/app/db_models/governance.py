"""Governance workflow models - for Governance Audit Log feature."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database.base import Base, UUIDMixin


class GovernanceTransition(Base, UUIDMixin):
    """Governance state transitions for documents - shown in Governance Audit Log."""
    
    __tablename__ = "governance_transitions"
    
    # Foreign key
    document_registry_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # State change
    from_state = Column(String(50))  # NULL for initial state
    to_state = Column(String(50), nullable=False, index=True)
    
    # Who changed it (just a string for now, no user table)
    changed_by = Column(String(255))
    reason = Column(Text)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), index=True)
    
    # Relationships
    document_registry = relationship("DocumentRegistry", back_populates="governance_transitions")

