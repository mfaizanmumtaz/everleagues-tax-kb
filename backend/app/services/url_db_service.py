"""PostgreSQL URL management service."""

from datetime import datetime
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from ..db_models.scrape_url import (
    ScrapeUrl,
    ApiCredential,
    DataSourceType,
    ScheduleFrequency,
    UrlStatus,
)


class UrlDbService:
    """Service for URL management using PostgreSQL."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def create_url(
        self,
        url: str,
        jurisdiction: str = "federal",  # Now accepts jurisdiction directly
        state: Optional[str] = None,
        city: Optional[str] = None,
        data_source: DataSourceType = DataSourceType.SCRAPE,
        schedule_frequency: ScheduleFrequency = ScheduleFrequency.ON_DEMAND,
        api_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        delay_between_requests: int = 2,
        max_requests_per_minute: int = 30,
        max_files_per_session: int = 10000,
    ) -> ScrapeUrl:
        """
        Create a new URL entry.

        Args:
            url: URL to scrape
            jurisdiction: federal, state, or local (required)
            state: State code (required for state/local)
            city: City name (required for local)
            data_source: scrape, api, or file
            schedule_frequency: How often to scrape
            api_endpoint: API endpoint (if data_source is api)
            api_key: API key (if data_source is api)
            name: Optional display name
            description: Optional description
            delay_between_requests: Seconds between requests
            max_requests_per_minute: Rate limit
            max_files_per_session: Max files to download

        Returns:
            Created ScrapeUrl object
        """
        # Jurisdiction is now provided directly (no derivation needed)
        # Create URL entry
        scrape_url = ScrapeUrl(
            url=url,
            name=name,
            description=description,
            category=None,  # Deprecated, use jurisdiction
            state=state,
            city=city,
            jurisdiction=jurisdiction.lower(),
            data_source=data_source,
            schedule_frequency=schedule_frequency,
            delay_between_requests=delay_between_requests,
            max_requests_per_minute=max_requests_per_minute,
            max_files_per_session=max_files_per_session,
            status=UrlStatus.ACTIVE,
            documents_count=0,
        )

        self.db.add(scrape_url)
        await self.db.flush()  # Get the ID

        # Create API credential if needed
        if data_source == DataSourceType.API and api_endpoint:
            credential = ApiCredential(
                scrape_url_id=scrape_url.id,
                api_endpoint=api_endpoint,
                api_key_encrypted=api_key.encode()
                if api_key
                else None,  # In production, encrypt this
            )
            self.db.add(credential)

        await self.db.commit()
        await self.db.refresh(scrape_url)

        return scrape_url

    async def get_url(self, url_id: UUID) -> Optional[ScrapeUrl]:
        """Get a URL by ID."""
        stmt = select(ScrapeUrl).where(ScrapeUrl.id == url_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_url_by_url(self, url: str) -> Optional[ScrapeUrl]:
        """Get a URL by its URL string."""
        stmt = select(ScrapeUrl).where(ScrapeUrl.url == url)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_urls(
        self,
        category: Optional[str] = None,
        state: Optional[str] = None,
        status: Optional[UrlStatus] = None,
        data_source: Optional[DataSourceType] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[ScrapeUrl], int]:
        """
        List URLs with filters and pagination.

        Returns:
            Tuple of (urls list, total count)
        """
        # Build conditions list
        conditions = []

        if category:
            conditions.append(ScrapeUrl.category == category)
        if state:
            conditions.append(ScrapeUrl.state == state)
        if status:
            conditions.append(ScrapeUrl.status == status)
        if data_source:
            conditions.append(ScrapeUrl.data_source == data_source)
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    ScrapeUrl.url.ilike(search_term),
                    ScrapeUrl.name.ilike(search_term),
                    ScrapeUrl.description.ilike(search_term),
                )
            )

        # Get total count
        count_stmt = select(func.count()).select_from(ScrapeUrl)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        # Get data with pagination
        offset = (page - 1) * limit
        data_stmt = select(ScrapeUrl)
        if conditions:
            data_stmt = data_stmt.where(*conditions)
        data_stmt = (
            data_stmt.order_by(ScrapeUrl.created_at.desc()).offset(offset).limit(limit)
        )
        result = await self.db.execute(data_stmt)
        urls = result.scalars().all()

        return urls, total

    async def update_url(self, url_id: UUID, **kwargs) -> Optional[ScrapeUrl]:
        """
        Update a URL entry.

        Args:
            url_id: URL ID
            **kwargs: Fields to update

        Returns:
            Updated ScrapeUrl object or None if not found
        """
        scrape_url = await self.get_url(url_id)
        if not scrape_url:
            return None

        # Map field names
        field_mapping = {
            "url": "url",
            "name": "name",
            "description": "description",
            "jurisdiction": "jurisdiction",  # Direct mapping, no derivation
            "state": "state",
            "city": "city",
            "data_source": "data_source",
            "schedule_frequency": "schedule_frequency",
            "status": "status",
            "delay_between_requests": "delay_between_requests",
            "max_requests_per_minute": "max_requests_per_minute",
            "max_files_per_session": "max_files_per_session",
            "error_message": "error_message",
        }

        for key, value in kwargs.items():
            if key in field_mapping and value is not None:
                # Normalize jurisdiction to lowercase
                if key == "jurisdiction" and isinstance(value, str):
                    value = value.lower()
                setattr(scrape_url, field_mapping[key], value)

        await self.db.commit()
        await self.db.refresh(scrape_url)

        return scrape_url

    async def update_url_status(
        self, url_id: UUID, status: UrlStatus, error_message: Optional[str] = None
    ) -> Optional[ScrapeUrl]:
        """Update URL status."""
        scrape_url = await self.get_url(url_id)
        if not scrape_url:
            return None

        scrape_url.status = status
        if error_message is not None:
            scrape_url.error_message = error_message

        if status == UrlStatus.ACTIVE and scrape_url.error_message:
            scrape_url.error_message = None

        await self.db.commit()
        await self.db.refresh(scrape_url)

        return scrape_url

    async def update_scrape_stats(
        self,
        url_id: UUID,
        documents_count: Optional[int] = None,
        last_scraped_at: Optional[datetime] = None,
        last_successful_at: Optional[datetime] = None,
    ) -> Optional[ScrapeUrl]:
        """Update scraping statistics."""
        scrape_url = await self.get_url(url_id)
        if not scrape_url:
            return None

        if documents_count is not None:
            scrape_url.documents_count = documents_count
        if last_scraped_at:
            scrape_url.last_scraped_at = last_scraped_at
        if last_successful_at:
            scrape_url.last_successful_at = last_successful_at

        await self.db.commit()
        await self.db.refresh(scrape_url)

        return scrape_url

    async def increment_documents_count(
        self, url_id: UUID, count: int = 1
    ) -> Optional[ScrapeUrl]:
        """Increment the documents count for a URL."""
        scrape_url = await self.get_url(url_id)
        if not scrape_url:
            return None

        scrape_url.documents_count = (scrape_url.documents_count or 0) + count
        await self.db.commit()
        await self.db.refresh(scrape_url)

        return scrape_url

    async def delete_url(self, url_id: UUID) -> bool:
        """
        Delete a URL entry.

        Returns:
            True if deleted, False if not found
        """
        scrape_url = await self.get_url(url_id)
        if not scrape_url:
            return False

        await self.db.delete(scrape_url)
        await self.db.commit()

        return True

    async def get_urls_for_scheduling(
        self, frequency: Optional[ScheduleFrequency] = None
    ) -> List[ScrapeUrl]:
        """Get URLs that need to be scheduled for scraping."""
        stmt = select(ScrapeUrl).where(
            ScrapeUrl.status == UrlStatus.ACTIVE,
            ScrapeUrl.schedule_frequency != ScheduleFrequency.ON_DEMAND,
        )

        if frequency:
            stmt = stmt.where(ScrapeUrl.schedule_frequency == frequency)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_api_credential(self, url_id: UUID) -> Optional[ApiCredential]:
        """Get API credential for a URL."""
        stmt = select(ApiCredential).where(ApiCredential.scrape_url_id == url_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def to_dict(self, scrape_url: ScrapeUrl) -> dict:
        """Convert ScrapeUrl to dictionary for API response."""
        return {
            "id": str(scrape_url.id),
            "url": scrape_url.url,
            "name": scrape_url.name,
            "description": scrape_url.description,
            "category": scrape_url.category,
            "state": scrape_url.state,
            "city": scrape_url.city,
            "jurisdiction": scrape_url.jurisdiction,
            "data_source": scrape_url.data_source.value
            if scrape_url.data_source
            else "scrape",
            "schedule_frequency": scrape_url.schedule_frequency.value
            if scrape_url.schedule_frequency
            else "on_demand",
            "status": scrape_url.status.value if scrape_url.status else "active",
            "error_message": scrape_url.error_message,
            "documents_count": scrape_url.documents_count or 0,
            "last_scraped": scrape_url.last_scraped_at.isoformat()
            if scrape_url.last_scraped_at
            else None,
            "delay_between_requests": scrape_url.delay_between_requests,
            "max_requests_per_minute": scrape_url.max_requests_per_minute,
            "max_files_per_session": scrape_url.max_files_per_session,
            "created_at": scrape_url.created_at.isoformat()
            if scrape_url.created_at
            else None,
            "updated_at": scrape_url.updated_at.isoformat()
            if scrape_url.updated_at
            else None,
        }
