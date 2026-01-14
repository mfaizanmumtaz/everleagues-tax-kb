"""PostgreSQL Uploaded File management service."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..db_models.scrape_url import UploadedFile, ProcessingStatus
from ..config import settings


class UploadedFileService:
    """Service for managing uploaded file records in PostgreSQL."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def create(
        self,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        file_size: int,
        mime_type: Optional[str] = None,
        checksum: Optional[str] = None,
        blob_container: Optional[str] = None,
        blob_path: Optional[str] = None,
        blob_url: Optional[str] = None,
    ) -> UploadedFile:
        """
        Create a new uploaded file record.

        Args:
            original_filename: Original name of the uploaded file
            stored_filename: UUID-based filename for storage
            file_path: Path in storage (Azure Blob or local)
            file_size: Size in bytes
            mime_type: MIME type of the file
            checksum: SHA-256 checksum
            blob_container: Azure Blob container name
            blob_path: Path within the container
            blob_url: Full URL to access the blob

        Returns:
            Created UploadedFile object
        """
        uploaded_file = UploadedFile(
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            checksum=checksum,
            blob_container=blob_container,
            blob_path=blob_path,
            blob_url=blob_url,
            processing_status=ProcessingStatus.PENDING,
        )

        self.db.add(uploaded_file)
        await self.db.commit()
        await self.db.refresh(uploaded_file)

        return uploaded_file

    async def get_by_id(self, file_id: UUID) -> Optional[UploadedFile]:
        """
        Get uploaded file by ID.

        Args:
            file_id: UUID of the uploaded file

        Returns:
            UploadedFile if found, None otherwise
        """
        stmt = select(UploadedFile).where(UploadedFile.id == file_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_checksum(self, checksum: str) -> Optional[UploadedFile]:
        """
        Get uploaded file by checksum for duplicate detection.

        Args:
            checksum: SHA-256 checksum of the file

        Returns:
            UploadedFile if found, None otherwise
        """
        stmt = select(UploadedFile).where(UploadedFile.checksum == checksum)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_processing_status(
        self,
        file_id: UUID,
        status: ProcessingStatus,
        error: Optional[str] = None,
    ) -> Optional[UploadedFile]:
        """
        Update the processing status of an uploaded file.

        Args:
            file_id: UUID of the uploaded file
            status: New processing status
            error: Error message if status is FAILED

        Returns:
            Updated UploadedFile if found, None otherwise
        """
        uploaded_file = await self.get_by_id(file_id)
        if not uploaded_file:
            return None

        uploaded_file.processing_status = status

        if error:
            uploaded_file.processing_error = error

        if status in (ProcessingStatus.COMPLETED, ProcessingStatus.FAILED):
            uploaded_file.processed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(uploaded_file)

        return uploaded_file

    async def update_solr_reference(
        self,
        file_id: UUID,
        solr_document_id: str,
    ) -> Optional[UploadedFile]:
        """
        Link uploaded file to its Solr document.

        Args:
            file_id: UUID of the uploaded file
            solr_document_id: ID of the document in Solr

        Returns:
            Updated UploadedFile if found, None otherwise
        """
        uploaded_file = await self.get_by_id(file_id)
        if not uploaded_file:
            return None

        uploaded_file.solr_document_id = solr_document_id

        await self.db.commit()
        await self.db.refresh(uploaded_file)

        return uploaded_file

    async def list_by_status(
        self,
        status: ProcessingStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> List[UploadedFile]:
        """
        List uploaded files by processing status.

        Args:
            status: Processing status to filter by
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of UploadedFile objects
        """
        stmt = (
            select(UploadedFile)
            .where(UploadedFile.processing_status == status)
            .order_by(UploadedFile.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete(self, file_id: UUID) -> bool:
        """
        Delete an uploaded file record.

        Args:
            file_id: UUID of the uploaded file

        Returns:
            True if deleted, False if not found
        """
        uploaded_file = await self.get_by_id(file_id)
        if not uploaded_file:
            return False

        await self.db.delete(uploaded_file)
        await self.db.commit()

        return True
