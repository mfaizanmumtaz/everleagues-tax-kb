"""Discovered Page service for managing discovered pages."""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from ..db_models.discovered_page import DiscoveredPage, PageStatus


class DiscoveredPageService:
    """Service for managing discovered pages."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def list_pages(
        self,
        scrape_url_id: UUID,
        status: Optional[PageStatus] = None,
        is_document: Optional[bool] = None,
        min_depth: Optional[int] = None,
        max_depth: Optional[int] = None,
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[DiscoveredPage], int]:
        """
        List discovered pages with filters and pagination.
        
        Args:
            scrape_url_id: Parent URL ID
            status: Filter by status
            is_document: Filter by document type
            min_depth: Minimum depth filter
            max_depth: Maximum depth filter
            page: Page number (1-indexed)
            limit: Items per page
            
        Returns:
            Tuple of (pages list, total count)
        """
        query = select(DiscoveredPage).where(
            DiscoveredPage.scrape_url_id == scrape_url_id
        )
        count_query = select(func.count(DiscoveredPage.id)).where(
            DiscoveredPage.scrape_url_id == scrape_url_id
        )

        if status is not None:
            query = query.where(DiscoveredPage.status == status)
            count_query = count_query.where(DiscoveredPage.status == status)
        
        if is_document is not None:
            query = query.where(DiscoveredPage.is_document == is_document)
            count_query = count_query.where(DiscoveredPage.is_document == is_document)
            
        if min_depth is not None:
            query = query.where(DiscoveredPage.depth >= min_depth)
            count_query = count_query.where(DiscoveredPage.depth >= min_depth)
            
        if max_depth is not None:
            query = query.where(DiscoveredPage.depth <= max_depth)
            count_query = count_query.where(DiscoveredPage.depth <= max_depth)

        # Get total count
        total = await self.db.execute(count_query)
        total_count = total.scalar() or 0

        # Apply pagination
        offset = (page - 1) * limit
        query = query.order_by(DiscoveredPage.depth, DiscoveredPage.path)
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        pages = result.scalars().all()

        return list(pages), total_count

    async def get_page(self, page_id: UUID) -> Optional[DiscoveredPage]:
        """Get a single discovered page by ID."""
        result = await self.db.execute(
            select(DiscoveredPage).where(DiscoveredPage.id == page_id)
        )
        return result.scalar_one_or_none()

    async def approve_pages(
        self,
        page_ids: List[UUID],
        reviewed_by: Optional[str] = None,
    ) -> int:
        """
        Approve multiple pages for ingestion.
        
        Args:
            page_ids: List of page IDs to approve
            reviewed_by: User who approved
            
        Returns:
            Number of pages approved
        """
        if not page_ids:
            return 0

        result = await self.db.execute(
            update(DiscoveredPage)
            .where(DiscoveredPage.id.in_(page_ids))
            .where(DiscoveredPage.status != PageStatus.INGESTED)
            .values(
                status=PageStatus.APPROVED,
                reviewed_at=datetime.now(timezone.utc),
                reviewed_by=reviewed_by,
            )
        )
        await self.db.commit()
        return result.rowcount

    async def reject_pages(
        self,
        page_ids: List[UUID],
        reviewed_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> int:
        """
        Reject pages (won't be ingested).
        
        Args:
            page_ids: List of page IDs to reject
            reviewed_by: User who rejected
            reason: Reason for rejection
            
        Returns:
            Number of pages rejected
        """
        if not page_ids:
            return 0

        result = await self.db.execute(
            update(DiscoveredPage)
            .where(DiscoveredPage.id.in_(page_ids))
            .where(DiscoveredPage.status != PageStatus.INGESTED)
            .values(
                status=PageStatus.REJECTED,
                reviewed_at=datetime.now(timezone.utc),
                reviewed_by=reviewed_by,
                rejection_reason=reason,
            )
        )
        await self.db.commit()
        return result.rowcount

    async def approve_all_pending(
        self,
        scrape_url_id: UUID,
        reviewed_by: Optional[str] = None,
    ) -> int:
        """Approve all pending pages for a URL."""
        result = await self.db.execute(
            update(DiscoveredPage)
            .where(DiscoveredPage.scrape_url_id == scrape_url_id)
            .where(DiscoveredPage.status == PageStatus.PENDING)
            .values(
                status=PageStatus.APPROVED,
                reviewed_at=datetime.now(timezone.utc),
                reviewed_by=reviewed_by,
            )
        )
        await self.db.commit()
        return result.rowcount

    async def reject_all_pending(
        self,
        scrape_url_id: UUID,
        reviewed_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> int:
        """Reject all pending pages for a URL."""
        result = await self.db.execute(
            update(DiscoveredPage)
            .where(DiscoveredPage.scrape_url_id == scrape_url_id)
            .where(DiscoveredPage.status == PageStatus.PENDING)
            .values(
                status=PageStatus.REJECTED,
                reviewed_at=datetime.now(timezone.utc),
                reviewed_by=reviewed_by,
                rejection_reason=reason,
            )
        )
        await self.db.commit()
        return result.rowcount

    async def get_approved_for_ingestion(
        self,
        scrape_url_id: UUID,
    ) -> List[DiscoveredPage]:
        """Get all approved pages ready for ingestion."""
        result = await self.db.execute(
            select(DiscoveredPage)
            .where(DiscoveredPage.scrape_url_id == scrape_url_id)
            .where(DiscoveredPage.status == PageStatus.APPROVED)
            .order_by(DiscoveredPage.depth, DiscoveredPage.path)
        )
        return list(result.scalars().all())

    async def mark_as_ingested(self, page_ids: List[UUID]) -> int:
        """Mark pages as ingested after successful scraping."""
        if not page_ids:
            return 0

        result = await self.db.execute(
            update(DiscoveredPage)
            .where(DiscoveredPage.id.in_(page_ids))
            .values(status=PageStatus.INGESTED)
        )
        await self.db.commit()
        return result.rowcount

    async def clear_discovered_pages(self, scrape_url_id: UUID) -> int:
        """
        Delete all discovered pages for a URL (for re-discovery).
        Only deletes non-ingested pages.
        """
        from sqlalchemy import delete
        
        result = await self.db.execute(
            delete(DiscoveredPage)
            .where(DiscoveredPage.scrape_url_id == scrape_url_id)
            .where(DiscoveredPage.status != PageStatus.INGESTED)
        )
        await self.db.commit()
        return result.rowcount

    def to_dict(self, page: DiscoveredPage) -> dict:
        """Convert DiscoveredPage to dictionary for API response."""
        return {
            "id": str(page.id),
            "scrape_url_id": str(page.scrape_url_id),
            "url": page.url,
            "path": page.path,
            "depth": page.depth,
            "title": page.title,
            "content_type": page.content_type,
            "content_length": page.content_length,
            "status": page.status.value,
            "is_document": page.is_document,
            "http_status": page.http_status,
            "reviewed_at": page.reviewed_at.isoformat() if page.reviewed_at else None,
            "reviewed_by": page.reviewed_by,
            "rejection_reason": page.rejection_reason,
            "discovered_at": page.discovered_at.isoformat() if page.discovered_at else None,
            "created_at": page.created_at.isoformat() if page.created_at else None,
        }
