"""Audit log service for PostgreSQL."""

from datetime import datetime
from typing import Optional, List, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_

from ..db_models.audit import AuditLog


class AuditLogService:
    """Service for audit log operations using PostgreSQL."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        actor: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        details: Optional[str] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            action: Action type (e.g., "document.create", "governance.change")
            resource_type: Resource type (e.g., "document", "url", "chunk")
            resource_id: ID of the resource
            resource_name: Display name of the resource
            actor: Who performed the action
            old_values: Previous values (for updates)
            new_values: New values (for creates/updates)
            details: Additional details text

        Returns:
            Created AuditLog object
        """
        log_entry = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            actor=actor,
            old_values=old_values,
            new_values=new_values,
            details=details,
        )

        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)

        return log_entry

    async def log_document_create(
        self,
        document_id: str,
        document_name: str,
        actor: Optional[str] = None,
        values: Optional[dict] = None,
    ) -> AuditLog:
        """Log document creation."""
        return await self.log_action(
            action="document.create",
            resource_type="document",
            resource_id=document_id,
            resource_name=document_name,
            actor=actor,
            new_values=values,
            details=f"Document '{document_name}' created",
        )

    async def log_document_update(
        self,
        document_id: str,
        document_name: str,
        actor: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
    ) -> AuditLog:
        """Log document update."""
        return await self.log_action(
            action="document.update",
            resource_type="document",
            resource_id=document_id,
            resource_name=document_name,
            actor=actor,
            old_values=old_values,
            new_values=new_values,
            details=f"Document '{document_name}' updated",
        )

    async def log_document_delete(
        self,
        document_id: str,
        document_name: str,
        actor: Optional[str] = None,
    ) -> AuditLog:
        """Log document deletion."""
        return await self.log_action(
            action="document.delete",
            resource_type="document",
            resource_id=document_id,
            resource_name=document_name,
            actor=actor,
            details=f"Document '{document_name}' deleted",
        )

    async def log_governance_change(
        self,
        document_id: str,
        document_name: str,
        from_state: Optional[str],
        to_state: str,
        actor: str,
        reason: Optional[str] = None,
    ) -> AuditLog:
        """Log governance state change."""
        return await self.log_action(
            action="governance.change",
            resource_type="document",
            resource_id=document_id,
            resource_name=document_name,
            actor=actor,
            old_values={"governance_state": from_state} if from_state else None,
            new_values={"governance_state": to_state, "reason": reason},
            details=f"Governance state changed from '{from_state}' to '{to_state}'" + (f": {reason}" if reason else ""),
        )

    async def log_url_create(
        self,
        url_id: str,
        url: str,
        actor: Optional[str] = None,
        values: Optional[dict] = None,
    ) -> AuditLog:
        """Log URL creation."""
        return await self.log_action(
            action="url.create",
            resource_type="url",
            resource_id=url_id,
            resource_name=url,
            actor=actor,
            new_values=values,
            details=f"URL '{url}' added",
        )

    async def log_url_scrape(
        self,
        url_id: str,
        url: str,
        actor: Optional[str] = None,
        documents_created: int = 0,
    ) -> AuditLog:
        """Log URL scraping."""
        return await self.log_action(
            action="url.scrape",
            resource_type="url",
            resource_id=url_id,
            resource_name=url,
            actor=actor,
            new_values={"documents_created": documents_created},
            details=f"Scraped URL '{url}', created {documents_created} documents",
        )

    async def log_url_delete(
        self,
        url_id: str,
        url: str,
        actor: Optional[str] = None,
    ) -> AuditLog:
        """Log URL deletion."""
        return await self.log_action(
            action="url.delete",
            resource_type="url",
            resource_id=url_id,
            resource_name=url,
            actor=actor,
            details=f"URL '{url}' deleted",
        )

    async def get_logs(
        self,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        actor: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[AuditLog], int]:
        """
        Get audit logs with filters and pagination.

        Returns:
            Tuple of (logs list, total count)
        """
        # Build filter conditions
        conditions = []
        if action:
            conditions.append(AuditLog.action == action)
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        if resource_id:
            conditions.append(AuditLog.resource_id == resource_id)
        if actor:
            conditions.append(AuditLog.actor == actor)
        if date_from:
            conditions.append(AuditLog.created_at >= date_from)
        if date_to:
            conditions.append(AuditLog.created_at <= date_to)
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    AuditLog.resource_name.ilike(search_term),
                    AuditLog.details.ilike(search_term),
                    AuditLog.actor.ilike(search_term),
                )
            )

        # Get total count
        count_stmt = select(func.count()).select_from(AuditLog).where(*conditions)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        # Apply pagination
        offset = (page - 1) * limit
        stmt = (
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        return logs, total

    async def get_logs_for_document(
        self,
        document_id: str,
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[AuditLog], int]:
        """Get all audit logs for a specific document."""
        return await self.get_logs(
            resource_type="document",
            resource_id=document_id,
            page=page,
            limit=limit,
        )

    async def get_governance_logs(
        self,
        document_id: Optional[str] = None,
        actor: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[AuditLog], int]:
        """Get governance-related audit logs."""
        conditions = [AuditLog.action == "governance.change"]

        if document_id:
            conditions.append(AuditLog.resource_id == document_id)
        if actor:
            conditions.append(AuditLog.actor == actor)

        # Count query
        count_stmt = select(func.count()).select_from(AuditLog).where(*conditions)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        # Data query
        offset = (page - 1) * limit
        stmt = (
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        return logs, total

    def to_dict(self, log: AuditLog) -> dict:
        """Convert AuditLog to dictionary for API response."""
        return {
            "id": str(log.id),
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "resource_name": log.resource_name,
            "actor": log.actor,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
