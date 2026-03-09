"""Pydantic models for audit log operations."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


# ==================== Audit Models ====================


class AuditLogResponse(BaseModel):
    """Audit log entry response."""

    id: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    actor: Optional[str] = None
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None
    details: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditLogsListResponse(BaseModel):
    """Response for audit logs list."""

    items: List[AuditLogResponse]
    total: int
    page: int
    limit: int
    pages: int
    has_next: bool
    has_prev: bool
