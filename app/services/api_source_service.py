"""PostgreSQL API source configuration management service."""

from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from ..db_models.api_source import (
    ApiSource,
    ApiSourceCategory,
    ApiSourceStatus,
    AuthType,
    FetchFrequency,
)


class ApiSourceService:
    """Service for API source configuration management using PostgreSQL."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def create(
        self,
        name: str,
        api_endpoint: str,
        description: Optional[str] = None,
        category: ApiSourceCategory = ApiSourceCategory.FEDERAL,
        auth_type: AuthType = AuthType.API_KEY,
        api_key: Optional[str] = None,
        oauth_token: Optional[str] = None,
        custom_headers: Optional[dict] = None,
        fetch_frequency: FetchFrequency = FetchFrequency.DAILY,
        max_file_size_mb: int = 50,
    ) -> ApiSource:
        """Create a new API source configuration."""
        source = ApiSource(
            name=name,
            description=description,
            api_endpoint=api_endpoint,
            category=category,
            status=ApiSourceStatus.ACTIVE,
            auth_type=auth_type,
            api_key_encrypted=api_key.encode() if api_key else None,
            oauth_token_encrypted=oauth_token.encode() if oauth_token else None,
            custom_headers=custom_headers,
            fetch_frequency=fetch_frequency,
            max_file_size_mb=max_file_size_mb,
            total_files_pushed=0,
        )

        self.db.add(source)
        await self.db.commit()
        await self.db.refresh(source)

        return source

    async def get_by_id(self, source_id: UUID) -> Optional[ApiSource]:
        """Get an API source by ID."""
        stmt = select(ApiSource).where(ApiSource.id == source_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        category: Optional[ApiSourceCategory] = None,
        status: Optional[ApiSourceStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[ApiSource], int]:
        """List API sources with filters and pagination."""
        conditions = []

        if category:
            conditions.append(ApiSource.category == category)
        if status:
            conditions.append(ApiSource.status == status)
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    ApiSource.name.ilike(search_term),
                    ApiSource.description.ilike(search_term),
                    ApiSource.api_endpoint.ilike(search_term),
                )
            )

        # Total count
        count_stmt = select(func.count()).select_from(ApiSource)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        # Paginated data
        offset = (page - 1) * limit
        data_stmt = select(ApiSource)
        if conditions:
            data_stmt = data_stmt.where(*conditions)
        data_stmt = (
            data_stmt.order_by(ApiSource.created_at.desc()).offset(offset).limit(limit)
        )
        result = await self.db.execute(data_stmt)
        sources = result.scalars().all()

        return sources, total

    async def update(self, source_id: UUID, **kwargs) -> Optional[ApiSource]:
        """Update an API source configuration."""
        source = await self.get_by_id(source_id)
        if not source:
            return None

        # Direct field updates
        direct_fields = {
            "name",
            "description",
            "api_endpoint",
            "category",
            "status",
            "auth_type",
            "custom_headers",
            "fetch_frequency",
            "max_file_size_mb",
            "error_message",
            "last_fetched_at",
            "total_files_pushed",
        }

        for key, value in kwargs.items():
            if key in direct_fields and value is not None:
                setattr(source, key, value)

        # Handle credential updates separately (encrypt)
        if "api_key" in kwargs:
            api_key = kwargs["api_key"]
            source.api_key_encrypted = api_key.encode() if api_key else None

        if "oauth_token" in kwargs:
            oauth_token = kwargs["oauth_token"]
            source.oauth_token_encrypted = (
                oauth_token.encode() if oauth_token else None
            )

        await self.db.commit()
        await self.db.refresh(source)

        return source

    async def delete(self, source_id: UUID) -> bool:
        """Delete an API source configuration."""
        source = await self.get_by_id(source_id)
        if not source:
            return False

        await self.db.delete(source)
        await self.db.commit()

        return True

    def to_response_dict(self, source: ApiSource) -> dict:
        """Convert ApiSource to dictionary for API response.

        Never exposes raw credentials -- only boolean flags.
        """
        return {
            "id": str(source.id),
            "name": source.name,
            "description": source.description,
            "api_endpoint": source.api_endpoint,
            "category": source.category.value if source.category else "federal",
            "status": source.status.value if source.status else "active",
            "auth_type": source.auth_type.value if source.auth_type else "api_key",
            "api_key_configured": source.api_key_encrypted is not None,
            "oauth_token_configured": source.oauth_token_encrypted is not None,
            "custom_headers": source.custom_headers,
            "fetch_frequency": (
                source.fetch_frequency.value if source.fetch_frequency else "daily"
            ),
            "max_file_size_mb": source.max_file_size_mb or 50,
            "last_fetched_at": (
                source.last_fetched_at.isoformat() if source.last_fetched_at else None
            ),
            "total_files_pushed": source.total_files_pushed or 0,
            "error_message": source.error_message,
            "created_at": (
                source.created_at.isoformat() if source.created_at else None
            ),
            "updated_at": (
                source.updated_at.isoformat() if source.updated_at else None
            ),
        }
