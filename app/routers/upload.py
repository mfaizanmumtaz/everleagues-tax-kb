"""File Upload API routes - using unified DocumentRegistry."""

import json
import logging
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
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.upload import FileUploadMetadata, FileUploadResponse
from ..database.connection import get_db
from ..services.blob_storage_service import get_blob_storage_service
from ..services.document_registry_service import DocumentRegistryService
from ..db_models.document_registry import ProcessingStatus
from ..worker.tasks import process_document

router = APIRouter(prefix="/upload", tags=["File Upload"])

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
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    metadata: str = Form(None, description="JSON string with document metadata"),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file and queue it for processing through the ingestion pipeline."""
    try:
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

        file_ext = os.path.splitext(file.filename)[1].lower()
        stored_filename = f"{uuid4()}{file_ext}"

        try:
            blob_path, blob_url, checksum, stored_size = blob_service.upload_file(
                container=settings.azure_container_uploads,
                file_data=file_content,
                filename=stored_filename,
                folder=None,
                metadata={
                    "upload_source": "api",
                    "original_filename": file.filename,
                    "content_type": file.content_type or "application/octet-stream",
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store file in blob storage: {str(e)}",
            )

        # Create DocumentRegistry entry with PENDING status
        registry_service = DocumentRegistryService(db)

        try:
            registry = await registry_service.create_for_upload(
                document_name=file.filename,
                source_url=blob_url,
                title=upload_metadata.title,
                jurisdiction=upload_metadata.jurisdiction,
                state=upload_metadata.state,
                city=upload_metadata.city,
                tax_year=upload_metadata.tax_year,
                doc_type=upload_metadata.doc_type,
            )

            # Create blob record
            await registry_service.create_blob(
                registry_id=registry.id,
                blob_type="raw",
                blob_container=settings.azure_container_uploads,
                blob_path=blob_path,
                blob_url=blob_url,
                original_filename=file.filename,
                file_size=file_size,
                mime_type=file.content_type,
                content_hash=checksum,
            )

            # Set status to QUEUED (Celery worker will set it to PROCESSING)
            await registry_service.update_processing_status(
                registry.id, ProcessingStatus.QUEUED
            )

            registry_id = str(registry.id)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create registry record: {str(e)}",
            )

        # Queue the processing task via Celery
        process_document.delay(
            registry_id=registry_id,
            metadata=upload_metadata.model_dump(),
            source="upload",
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
            status="queued",
            chunks_created=0,
            word_count=0,
            page_count=0,
            parsing_quality=0.0,
            message="File uploaded successfully. Queued for processing.",
            document=None,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unexpected error during file upload: {str(e)}"
        )
