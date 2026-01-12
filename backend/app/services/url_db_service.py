"""PostgreSQL URL management service."""

from datetime import datetime
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from ..db_models.scrape_url import (
    ScrapeUrl,
    ApiCredential,
    DataSourceType,
    ScheduleFrequency,
    UrlStatus
)


class UrlDbService:
    """Service for URL management using PostgreSQL."""
    
    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
    
    def create_url(
        self,
        url: str,
        category: str = "Federal",
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
            category: Federal, State, or Local
            state: State code (for State/Local)
            city: City name (for Local)
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
        # Determine jurisdiction from category
        jurisdiction = "federal"
        if category.lower() == "state":
            jurisdiction = "state"
        elif category.lower() == "local":
            jurisdiction = "local"
        
        # Create URL entry
        scrape_url = ScrapeUrl(
            url=url,
            name=name,
            description=description,
            category=category,
            state=state,
            city=city,
            jurisdiction=jurisdiction,
            data_source=data_source,
            schedule_frequency=schedule_frequency,
            delay_between_requests=delay_between_requests,
            max_requests_per_minute=max_requests_per_minute,
            max_files_per_session=max_files_per_session,
            status=UrlStatus.ACTIVE,
            documents_count=0,
        )
        
        self.db.add(scrape_url)
        self.db.flush()  # Get the ID
        
        # Create API credential if needed
        if data_source == DataSourceType.API and api_endpoint:
            credential = ApiCredential(
                scrape_url_id=scrape_url.id,
                api_endpoint=api_endpoint,
                api_key_encrypted=api_key.encode() if api_key else None,  # In production, encrypt this
            )
            self.db.add(credential)
        
        self.db.commit()
        self.db.refresh(scrape_url)
        
        return scrape_url
    
    def get_url(self, url_id: UUID) -> Optional[ScrapeUrl]:
        """Get a URL by ID."""
        return self.db.query(ScrapeUrl).filter(ScrapeUrl.id == url_id).first()
    
    def get_url_by_url(self, url: str) -> Optional[ScrapeUrl]:
        """Get a URL by its URL string."""
        return self.db.query(ScrapeUrl).filter(ScrapeUrl.url == url).first()
    
    def list_urls(
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
        query = self.db.query(ScrapeUrl)
        
        # Apply filters
        if category:
            query = query.filter(ScrapeUrl.category == category)
        if state:
            query = query.filter(ScrapeUrl.state == state)
        if status:
            query = query.filter(ScrapeUrl.status == status)
        if data_source:
            query = query.filter(ScrapeUrl.data_source == data_source)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    ScrapeUrl.url.ilike(search_term),
                    ScrapeUrl.name.ilike(search_term),
                    ScrapeUrl.description.ilike(search_term),
                )
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        urls = query.order_by(ScrapeUrl.created_at.desc()).offset(offset).limit(limit).all()
        
        return urls, total
    
    def update_url(
        self,
        url_id: UUID,
        **kwargs
    ) -> Optional[ScrapeUrl]:
        """
        Update a URL entry.
        
        Args:
            url_id: URL ID
            **kwargs: Fields to update
        
        Returns:
            Updated ScrapeUrl object or None if not found
        """
        scrape_url = self.get_url(url_id)
        if not scrape_url:
            return None
        
        # Map field names
        field_mapping = {
            "url": "url",
            "name": "name",
            "description": "description",
            "category": "category",
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
                setattr(scrape_url, field_mapping[key], value)
        
        # Update jurisdiction if category changed
        if "category" in kwargs and kwargs["category"]:
            category = kwargs["category"].lower()
            if category == "federal":
                scrape_url.jurisdiction = "federal"
            elif category == "state":
                scrape_url.jurisdiction = "state"
            elif category == "local":
                scrape_url.jurisdiction = "local"
        
        self.db.commit()
        self.db.refresh(scrape_url)
        
        return scrape_url
    
    def update_url_status(
        self,
        url_id: UUID,
        status: UrlStatus,
        error_message: Optional[str] = None
    ) -> Optional[ScrapeUrl]:
        """Update URL status."""
        scrape_url = self.get_url(url_id)
        if not scrape_url:
            return None
        
        scrape_url.status = status
        if error_message is not None:
            scrape_url.error_message = error_message
        
        if status == UrlStatus.ACTIVE and scrape_url.error_message:
            scrape_url.error_message = None
        
        self.db.commit()
        self.db.refresh(scrape_url)
        
        return scrape_url
    
    def update_scrape_stats(
        self,
        url_id: UUID,
        documents_count: Optional[int] = None,
        last_scraped_at: Optional[datetime] = None,
        last_successful_at: Optional[datetime] = None,
    ) -> Optional[ScrapeUrl]:
        """Update scraping statistics."""
        scrape_url = self.get_url(url_id)
        if not scrape_url:
            return None
        
        if documents_count is not None:
            scrape_url.documents_count = documents_count
        if last_scraped_at:
            scrape_url.last_scraped_at = last_scraped_at
        if last_successful_at:
            scrape_url.last_successful_at = last_successful_at
        
        self.db.commit()
        self.db.refresh(scrape_url)
        
        return scrape_url
    
    def increment_documents_count(self, url_id: UUID, count: int = 1) -> Optional[ScrapeUrl]:
        """Increment the documents count for a URL."""
        scrape_url = self.get_url(url_id)
        if not scrape_url:
            return None
        
        scrape_url.documents_count = (scrape_url.documents_count or 0) + count
        self.db.commit()
        self.db.refresh(scrape_url)
        
        return scrape_url
    
    def delete_url(self, url_id: UUID) -> bool:
        """
        Delete a URL entry.
        
        Returns:
            True if deleted, False if not found
        """
        scrape_url = self.get_url(url_id)
        if not scrape_url:
            return False
        
        self.db.delete(scrape_url)
        self.db.commit()
        
        return True
    
    def get_urls_for_scheduling(
        self,
        frequency: Optional[ScheduleFrequency] = None
    ) -> List[ScrapeUrl]:
        """Get URLs that need to be scheduled for scraping."""
        query = self.db.query(ScrapeUrl).filter(
            ScrapeUrl.status == UrlStatus.ACTIVE,
            ScrapeUrl.schedule_frequency != ScheduleFrequency.ON_DEMAND,
        )
        
        if frequency:
            query = query.filter(ScrapeUrl.schedule_frequency == frequency)
        
        return query.all()
    
    def get_api_credential(self, url_id: UUID) -> Optional[ApiCredential]:
        """Get API credential for a URL."""
        return self.db.query(ApiCredential).filter(
            ApiCredential.scrape_url_id == url_id
        ).first()
    
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
            "data_source": scrape_url.data_source.value if scrape_url.data_source else "scrape",
            "schedule_frequency": scrape_url.schedule_frequency.value if scrape_url.schedule_frequency else "on_demand",
            "status": scrape_url.status.value if scrape_url.status else "active",
            "error_message": scrape_url.error_message,
            "documents_count": scrape_url.documents_count or 0,
            "last_scraped": scrape_url.last_scraped_at.isoformat() if scrape_url.last_scraped_at else None,
            "delay_between_requests": scrape_url.delay_between_requests,
            "max_requests_per_minute": scrape_url.max_requests_per_minute,
            "max_files_per_session": scrape_url.max_files_per_session,
            "created_at": scrape_url.created_at.isoformat() if scrape_url.created_at else None,
            "updated_at": scrape_url.updated_at.isoformat() if scrape_url.updated_at else None,
        }

