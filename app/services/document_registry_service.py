"""PostgreSQL Document Registry management service."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db_models.document_registry import (
    DocumentRegistry,
    DocumentBlob,
    SourceType,
    ProcessingStatus,
)


class DocumentRegistryService:
    """Service for managing document registry entries in PostgreSQL."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_for_upload(
        self,
        document_name: str,
        source_url: Optional[str] = None,
        title: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        tax_year: Optional[int] = None,
        doc_type: Optional[str] = None,
    ) -> DocumentRegistry:
        """Create a registry entry for a file upload (starts in PENDING status)."""
        registry = DocumentRegistry(
            source_type=SourceType.UPLOAD,
            processing_status=ProcessingStatus.PENDING,
            document_name=document_name,
            title=title or document_name,
            jurisdiction=jurisdiction,
            state=state,
            city=city,
            tax_year=tax_year,
            doc_type=doc_type,
            source_url=source_url,
            governance_state="pending",
            version=1,
            is_latest=True,
            chunk_count=0,
        )

        self.db.add(registry)
        await self.db.commit()
        await self.db.refresh(registry)
        return registry

    async def create_for_scrape(
        self,
        scrape_url_id: UUID,
        scrape_job_id: UUID,
        document_name: str,
        source_url: Optional[str] = None,
        title: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        tax_year: Optional[int] = None,
        doc_type: Optional[str] = None,
    ) -> DocumentRegistry:
        """Create a registry entry for a scraped document."""
        registry = DocumentRegistry(
            source_type=SourceType.SCRAPE,
            processing_status=ProcessingStatus.PENDING,
            scrape_url_id=scrape_url_id,
            scrape_job_id=scrape_job_id,
            document_name=document_name,
            title=title or document_name,
            jurisdiction=jurisdiction,
            state=state,
            city=city,
            tax_year=tax_year,
            doc_type=doc_type,
            source_url=source_url,
            governance_state="pending",
            version=1,
            is_latest=True,
            chunk_count=0,
        )

        self.db.add(registry)
        await self.db.commit()
        await self.db.refresh(registry)
        return registry

    async def update_processing_status(
        self,
        registry_id: UUID,
        status: ProcessingStatus,
        error: Optional[str] = None,
    ) -> Optional[DocumentRegistry]:
        """Update the processing status of a document."""
        registry = await self.get_by_id(registry_id)
        if not registry:
            return None

        registry.processing_status = status
        if error:
            registry.processing_error = error
        if status in (ProcessingStatus.COMPLETED, ProcessingStatus.FAILED):
            registry.processed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(registry)
        return registry

    async def update_solr_reference(
        self,
        registry_id: UUID,
        solr_document_id: str,
    ) -> Optional[DocumentRegistry]:
        """Link registry entry to its Solr document."""
        registry = await self.get_by_id(registry_id)
        if not registry:
            return None

        registry.solr_document_id = solr_document_id
        await self.db.commit()
        await self.db.refresh(registry)
        return registry

    async def get_by_id(self, registry_id: UUID) -> Optional[DocumentRegistry]:
        stmt = select(DocumentRegistry).where(DocumentRegistry.id == registry_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_solr_id(self, solr_document_id: str) -> Optional[DocumentRegistry]:
        stmt = select(DocumentRegistry).where(
            DocumentRegistry.solr_document_id == solr_document_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_content_hash(self, content_hash: str) -> Optional[DocumentRegistry]:
        """Find registry by blob content hash for duplicate detection."""
        stmt = (
            select(DocumentRegistry)
            .join(DocumentBlob)
            .where(DocumentBlob.content_hash == content_hash)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_chunk_count(
        self,
        registry_id: UUID,
        chunk_count: int,
    ) -> Optional[DocumentRegistry]:
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
        original_filename: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        content_hash: Optional[str] = None,
    ) -> Optional[DocumentBlob]:
        """Create a blob reference for a document."""
        registry = await self.get_by_id(registry_id)
        if not registry:
            return None

        blob = DocumentBlob(
            document_registry_id=registry_id,
            blob_type=blob_type,
            blob_container=blob_container,
            blob_path=blob_path,
            blob_url=blob_url,
            original_filename=original_filename,
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

    async def list_by_status(
        self,
        status: ProcessingStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DocumentRegistry]:
        """List documents by processing status."""
        stmt = (
            select(DocumentRegistry)
            .where(DocumentRegistry.processing_status == status)
            .order_by(DocumentRegistry.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_source_type(
        self,
        source_type: SourceType,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DocumentRegistry]:
        """List documents by source type."""
        stmt = (
            select(DocumentRegistry)
            .where(DocumentRegistry.source_type == source_type)
            .order_by(DocumentRegistry.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_jurisdiction(
        self,
        jurisdiction: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DocumentRegistry]:
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
        registry = await self.get_by_id(registry_id)
        if not registry:
            return False

        await self.db.delete(registry)
        await self.db.commit()
        return True

    async def delete_by_solr_id(self, solr_document_id: str) -> bool:
        registry = await self.get_by_solr_id(solr_document_id)
        if not registry:
            return False

        await self.db.delete(registry)
        await self.db.commit()
        return True
