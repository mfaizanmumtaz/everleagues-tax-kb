"""PostgreSQL Document Registry management service."""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db_models.document_registry import DocumentRegistry, DocumentBlob


class DocumentRegistryService:
    """Service for managing document registry entries in PostgreSQL."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def create(
        self,
        solr_document_id: str,
        document_name: Optional[str] = None,
        title: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        tax_year: Optional[int] = None,
        governance_state: Optional[str] = None,
        doc_type: Optional[str] = None,
        category: Optional[str] = None,
        source_url: Optional[str] = None,
        scrape_url_id: Optional[UUID] = None,
        uploaded_file_id: Optional[UUID] = None,
        scrape_job_id: Optional[UUID] = None,
    ) -> DocumentRegistry:
        """
        Create a new document registry entry.

        Links a Solr document to its source (scrape URL, uploaded file, or scrape job).

        Args:
            solr_document_id: ID of the document in Solr
            document_name: Document filename/name
            title: Document title
            jurisdiction: federal, state, or local
            state: State code
            city: City name (for local jurisdiction)
            tax_year: Applicable tax year
            governance_state: Current governance state
            doc_type: Type of document
            category: Document category
            source_url: Source URL for reference
            scrape_url_id: FK to scrape_urls table
            uploaded_file_id: FK to uploaded_files table
            scrape_job_id: FK to scrape_jobs table

        Returns:
            Created DocumentRegistry object
        """
        registry = DocumentRegistry(
            solr_document_id=solr_document_id,
            document_name=document_name,
            title=title,
            jurisdiction=jurisdiction,
            state=state,
            city=city,
            tax_year=tax_year,
            governance_state=governance_state,
            doc_type=doc_type,
            category=category,
            source_url=source_url,
            scrape_url_id=scrape_url_id,
            uploaded_file_id=uploaded_file_id,
            scrape_job_id=scrape_job_id,
            version=1,
            is_latest=True,
            chunk_count=0,
        )

        self.db.add(registry)
        await self.db.commit()
        await self.db.refresh(registry)

        return registry

    async def get_by_id(self, registry_id: UUID) -> Optional[DocumentRegistry]:
        """
        Get document registry entry by ID.

        Args:
            registry_id: UUID of the registry entry

        Returns:
            DocumentRegistry if found, None otherwise
        """
        stmt = select(DocumentRegistry).where(DocumentRegistry.id == registry_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_solr_id(self, solr_document_id: str) -> Optional[DocumentRegistry]:
        """
        Get document registry entry by Solr document ID.

        Args:
            solr_document_id: ID of the document in Solr

        Returns:
            DocumentRegistry if found, None otherwise
        """
        stmt = select(DocumentRegistry).where(
            DocumentRegistry.solr_document_id == solr_document_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_uploaded_file(
        self,
        uploaded_file_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DocumentRegistry]:
        """
        Get document registry entries associated with an uploaded file.

        Args:
            uploaded_file_id: UUID of the uploaded file
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of DocumentRegistry objects
        """
        stmt = (
            select(DocumentRegistry)
            .where(DocumentRegistry.uploaded_file_id == uploaded_file_id)
            .order_by(DocumentRegistry.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_chunk_count(
        self,
        registry_id: UUID,
        chunk_count: int,
    ) -> Optional[DocumentRegistry]:
        """
        Update the denormalized chunk count for a document.

        Args:
            registry_id: UUID of the registry entry
            chunk_count: New chunk count

        Returns:
            Updated DocumentRegistry if found, None otherwise
        """
        registry = await self.get_by_id(registry_id)
        if not registry:
            return None

        registry.chunk_count = chunk_count

        await self.db.commit()
        await self.db.refresh(registry)

        return registry

    async def update_governance_state(
        self,
        registry_id: UUID,
        governance_state: str,
    ) -> Optional[DocumentRegistry]:
        """
        Update the governance state of a document.

        Args:
            registry_id: UUID of the registry entry
            governance_state: New governance state

        Returns:
            Updated DocumentRegistry if found, None otherwise
        """
        registry = await self.get_by_id(registry_id)
        if not registry:
            return None

        registry.governance_state = governance_state

        await self.db.commit()
        await self.db.refresh(registry)

        return registry

    async def create_blob(
        self,
        registry_id: UUID,
        blob_type: str,
        blob_container: str,
        blob_path: str,
        blob_url: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        content_hash: Optional[str] = None,
    ) -> Optional[DocumentBlob]:
        """
        Create a blob reference for a document.

        Args:
            registry_id: UUID of the registry entry
            blob_type: Type of blob (raw, processed, chunk)
            blob_container: Azure Blob container name
            blob_path: Path within the container
            blob_url: Full URL to access the blob
            file_size: Size in bytes
            mime_type: MIME type
            content_hash: SHA-256 hash for deduplication

        Returns:
            Created DocumentBlob if registry found, None otherwise
        """
        registry = await self.get_by_id(registry_id)
        if not registry:
            return None

        blob = DocumentBlob(
            document_registry_id=registry_id,
            blob_type=blob_type,
            blob_container=blob_container,
            blob_path=blob_path,
            blob_url=blob_url,
            file_size=file_size,
            mime_type=mime_type,
            content_hash=content_hash,
            version=1,
            is_current=True,
        )

        self.db.add(blob)
        await self.db.commit()
        await self.db.refresh(blob)

        return blob

    async def list_by_jurisdiction(
        self,
        jurisdiction: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DocumentRegistry]:
        """
        List document registry entries by jurisdiction.

        Args:
            jurisdiction: Jurisdiction to filter by (federal, state, local)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of DocumentRegistry objects
        """
        stmt = (
            select(DocumentRegistry)
            .where(
                DocumentRegistry.jurisdiction == jurisdiction,
                DocumentRegistry.is_latest == True,
            )
            .order_by(DocumentRegistry.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete(self, registry_id: UUID) -> bool:
        """
        Delete a document registry entry and its associated blobs.

        Args:
            registry_id: UUID of the registry entry

        Returns:
            True if deleted, False if not found
        """
        registry = await self.get_by_id(registry_id)
        if not registry:
            return False

        await self.db.delete(registry)
        await self.db.commit()

        return True
