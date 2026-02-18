"""API Push routes - for external API download service to push files."""

import logging
import json
import os
from typing import Optional
from uuid import uuid4, UUID
from fastapi import (
    APIRouter,
    HTTPException,
    File,
    UploadFile,
    Form,
    Depends,
    Query,
    Path,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.upload import FileUploadMetadata, FileUploadResponse
from ..database.connection import get_db
from ..services.blob_storage_service import get_blob_storage_service
from ..services.document_service import get_document_service
from ..services.document_registry_service import DocumentRegistryService
from ..db_models.document_registry import ProcessingStatus, SourceType
from ..worker.tasks import process_document

router = APIRouter(prefix="/push", tags=["API Push"])

logger = logging.getLogger(__name__)


def _validate_file_size(file_size: int) -> None:
    max_size = settings.max_upload_size_bytes
    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb}MB",
        )


def _validate_file_type(filename: str) -> None:
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    if ext not in settings.allowed_file_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported types: {', '.join(settings.allowed_file_extensions)}",
        )


def _parse_metadata(metadata_str: Optional[str]) -> FileUploadMetadata:
    if not metadata_str:
        return FileUploadMetadata()

    try:
        metadata_dict = json.loads(metadata_str)
        return FileUploadMetadata(**metadata_dict)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid metadata JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing metadata: {str(e)}")


@router.post("", response_model=FileUploadResponse, status_code=201)
async def push_file(
    file: UploadFile = File(..., description="File to push"),
    file_id: str = Form(..., description="External file ID from API download service"),
    metadata: str = Form(None, description="JSON string with document metadata"),
    db: AsyncSession = Depends(get_db),
):
    """
    Push a file from an external API download service.

    If a file with the same file_id already exists, it will be replaced
    and flagged for review.
    """
    try:
        logger.info(f"API Push started: file_id={file_id}, filename={file.filename}")

        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        _validate_file_type(file.filename)

        file_content = await file.read()
        file_size = len(file_content)

        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        _validate_file_size(file_size)

        upload_metadata = _parse_metadata(metadata)

        blob_service = get_blob_storage_service()

        if not blob_service.is_configured():
            raise HTTPException(
                status_code=503, detail="Azure Blob Storage is not configured"
            )

        # Check if file_id already exists (replacement scenario)
        registry_service = DocumentRegistryService(db)
        existing_registry = await registry_service.get_by_external_file_id(file_id)
        is_replacement = existing_registry is not None

        if is_replacement:
            logger.info(f"Replacement detected for file_id={file_id}, existing registry_id={existing_registry.id}")

            # Delete old Solr document and chunks if exists
            if existing_registry.solr_document_id:
                try:
                    doc_service = get_document_service()
                    await doc_service.delete_document(existing_registry.solr_document_id)
                    logger.info(f"Deleted old Solr document: {existing_registry.solr_document_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete old Solr document: {e}")

            # Mark for replacement (sets needs_review=True)
            await registry_service.mark_for_replacement(existing_registry.id)
            registry_id = str(existing_registry.id)
        else:
            # Create new registry entry
            registry = await registry_service.create_for_api_push(
                external_file_id=file_id,
                document_name=file.filename,
                source_url=None,
                title=upload_metadata.title,
                jurisdiction=upload_metadata.jurisdiction,
                state=upload_metadata.state,
                city=upload_metadata.city,
                tax_year=upload_metadata.tax_year,
                doc_type=upload_metadata.doc_type,
            )
            registry_id = str(registry.id)

        # Upload to API-pushed container
        file_ext = os.path.splitext(file.filename)[1].lower()
        stored_filename = f"{uuid4()}{file_ext}"

        try:
            logger.info(f"Uploading to blob storage (api-pushed): {stored_filename}")
            blob_path, blob_url, checksum, stored_size = blob_service.upload_file(
                container=settings.azure_container_api_pushed,
                file_data=file_content,
                filename=stored_filename,
                folder=None,
                metadata={
                    "upload_source": "api_push",
                    "external_file_id": file_id,
                    "original_filename": file.filename,
                    "content_type": file.content_type or "application/octet-stream",
                    "is_replacement": str(is_replacement),
                },
            )
        except Exception as e:
            logger.error(f"Blob storage upload failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store file in blob storage: {str(e)}",
            )

        logger.info(f"Blob upload complete for file_id={file_id}")

        # Create blob record
        await registry_service.create_blob(
            registry_id=UUID(registry_id),
            blob_type="raw",
            blob_container=settings.azure_container_api_pushed,
            blob_path=blob_path,
            blob_url=blob_url,
            original_filename=file.filename,
            file_size=file_size,
            mime_type=file.content_type,
            content_hash=checksum,
        )

        # Set status to QUEUED (Celery worker will set it to PROCESSING)
        await registry_service.update_processing_status(
            UUID(registry_id), ProcessingStatus.QUEUED
        )

        # Queue the processing task via Celery
        process_document.delay(
            registry_id=registry_id,
            metadata=upload_metadata.model_dump(),
            source="api_push",
            is_replacement=is_replacement,
        )

        response = FileUploadResponse(
            document_id="pending",
            uploaded_file_id=None,
            registry_id=registry_id,
            filename=file.filename,
            file_size=file_size,
            blob_path=blob_path,
            blob_url=blob_url,
            content_type=file.content_type or "application/octet-stream",
            status="queued" if not is_replacement else "replacing",
            chunks_created=0,
            word_count=0,
            page_count=0,
            parsing_quality=0.0,
            message=f"File {'replaced' if is_replacement else 'pushed'} successfully. Queued for processing.",
            document=None,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during API push: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Unexpected error during API push: {str(e)}"
        )


@router.get("/list")
async def list_pushed_files(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    needs_review: Optional[bool] = Query(default=None, description="Filter by review status"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all files pushed via the API download service.

    Used for sync operations or to identify files needing review after replacement.
    """
    try:
        registry_service = DocumentRegistryService(db)
        offset = (page - 1) * limit

        registries = await registry_service.list_by_source_type(
            source_type=SourceType.API,
            limit=limit,
            offset=offset,
        )

        # Filter by needs_review if specified
        if needs_review is not None:
            registries = [r for r in registries if r.needs_review == needs_review]

        items = [
            {
                "registry_id": str(r.id),
                "external_file_id": r.external_file_id,
                "document_name": r.document_name,
                "title": r.title,
                "processing_status": r.processing_status.value if r.processing_status else None,
                "solr_document_id": r.solr_document_id,
                "needs_review": r.needs_review,
                "replaced_at": r.replaced_at.isoformat() if r.replaced_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "jurisdiction": r.jurisdiction,
                "state": r.state,
                "chunk_count": r.chunk_count,
            }
            for r in registries
        ]

        return {
            "items": items,
            "page": page,
            "limit": limit,
            "total": len(items),
        }
    except Exception as e:
        logger.exception(f"Error listing pushed files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{file_id}", status_code=204)
async def delete_pushed_file(
    file_id: str = Path(..., description="External file ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a file that was pushed via the API download service.

    Removes the document from Solr, blob storage, and the registry.
    """
    try:
        registry_service = DocumentRegistryService(db)

        # Find by external file_id
        registry = await registry_service.get_by_external_file_id(file_id)

        if not registry:
            raise HTTPException(
                status_code=404,
                detail=f"File with ID '{file_id}' not found"
            )

        # Delete from Solr if exists
        if registry.solr_document_id:
            try:
                doc_service = get_document_service()
                await doc_service.delete_document(registry.solr_document_id)
                logger.info(f"Deleted Solr document: {registry.solr_document_id}")
            except Exception as e:
                logger.warning(f"Failed to delete Solr document: {e}")

        # Delete blob(s)
        blob_service = get_blob_storage_service()
        for blob in registry.blobs:
            try:
                blob_service.delete_file(blob.blob_container, blob.blob_path)
                logger.info(f"Deleted blob: {blob.blob_path}")
            except Exception as e:
                logger.warning(f"Failed to delete blob: {e}")

        # Delete registry (cascades to blobs table)
        await registry_service.delete(registry.id)

        logger.info(f"Deleted pushed file: file_id={file_id}, registry_id={registry.id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting pushed file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
