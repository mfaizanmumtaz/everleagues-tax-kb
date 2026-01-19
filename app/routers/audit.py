"""Audit Log API routes."""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db
from ..services.audit_log_service import AuditLogService

router = APIRouter(prefix="/audit", tags=["Audit"])


# ==================== Pydantic Models ====================


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


# ==================== API Endpoints ====================


@router.get("/logs", response_model=AuditLogsListResponse)
async def list_audit_logs(
    action: Optional[str] = Query(default=None, description="Filter by action type"),
    resource_type: Optional[str] = Query(
        default=None, description="Filter by resource type"
    ),
    resource_id: Optional[str] = Query(
        default=None, description="Filter by resource ID"
    ),
    actor: Optional[str] = Query(default=None, description="Filter by actor"),
    date_from: Optional[datetime] = Query(default=None, description="Filter from date"),
    date_to: Optional[datetime] = Query(default=None, description="Filter to date"),
    search: Optional[str] = Query(default=None, description="Search in details"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    List audit logs with filters and pagination.
    """
    try:
        audit_service = AuditLogService(db)

        logs, total = await audit_service.get_logs(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor=actor,
            date_from=date_from,
            date_to=date_to,
            search=search,
            page=page,
            limit=limit,
        )

        pages = (total + limit - 1) // limit if total > 0 else 1

        items = [AuditLogResponse(**audit_service.to_dict(log)) for log in logs]

        return AuditLogsListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/document/{document_id}", response_model=AuditLogsListResponse)
async def get_document_audit_logs(
    document_id: str = Path(..., description="Document ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all audit logs for a specific document.
    """
    try:
        audit_service = AuditLogService(db)

        logs, total = await audit_service.get_logs_for_document(
            document_id=document_id,
            page=page,
            limit=limit,
        )

        pages = (total + limit - 1) // limit if total > 0 else 1

        items = [AuditLogResponse(**audit_service.to_dict(log)) for log in logs]

        return AuditLogsListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/governance", response_model=AuditLogsListResponse)
async def get_governance_audit_logs(
    document_id: Optional[str] = Query(
        default=None, description="Filter by document ID"
    ),
    actor: Optional[str] = Query(default=None, description="Filter by actor"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get governance-related audit logs.

    This returns logs for governance state changes only.
    """
    try:
        audit_service = AuditLogService(db)

        logs, total = await audit_service.get_governance_logs(
            document_id=document_id,
            actor=actor,
            page=page,
            limit=limit,
        )

        pages = (total + limit - 1) // limit if total > 0 else 1

        items = [AuditLogResponse(**audit_service.to_dict(log)) for log in logs]

        return AuditLogsListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
