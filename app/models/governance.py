"""Pydantic models for governance operations."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from .common import GovernanceState


# ==================== Governance Models ====================


class GovernanceLogEntry(BaseModel):
    """A governance log entry."""

    id: str
    document_id: str
    document_name: str
    from_state: Optional[str] = None
    to_state: str
    changed_by: str
    reason: Optional[str] = None
    timestamp: datetime


class GovernanceLogsResponse(BaseModel):
    """Response for governance logs."""

    items: List[GovernanceLogEntry]
    total: int
    page: int
    limit: int
    pages: int
    has_next: bool
    has_prev: bool


class GovernanceLogCreate(BaseModel):
    """Request to create a governance log entry."""

    document_id: str = Field(..., description="Document ID")
    to_state: GovernanceState = Field(..., description="New governance state")
    changed_by: str = Field(..., description="User who made the change")
    reason: Optional[str] = Field(default=None, description="Reason for the change")
