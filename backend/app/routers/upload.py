"""File Upload API routes."""

import asyncio
import json
import os
from typing import Optional
from datetime import datetime
from uuid import uuid4
from fastapi import (
    APIRouter,
    HTTPException,
    File,
    UploadFile,
    Form,
    Depends,
    BackgroundTasks,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.upload import FileUploadMetadata, FileUploadResponse
from ..models.document import DocumentCreate
from ..database.connection import get_db
from ..services.blob_storage_service import get_blob_storage_service
from ..services.file_parser import get_file_parser_service
from ..services.document_service import get_document_service
from ..services.document_classifier_service import get_document_classifier_service
from ..services.audit_log_service import AuditLogService
from ..services.uploaded_file_service import UploadedFileService
from ..services.document_registry_service import DocumentRegistryService
from ..db_models.scrape_url import ProcessingStatus

router = APIRouter(prefix="/upload", tags=["File Upload"])


def _validate_file_size(file_size: int) -> None:
    """Validate file size against maximum allowed."""
    max_size = settings.max_upload_size_bytes
    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb}MB",
        )


def _validate_file_type(filename: str) -> None:
    """Validate file extension is in allowed list."""
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    if ext not in settings.allowed_file_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported types: {', '.join(settings.allowed_file_extensions)}",
        )


def _parse_metadata(metadata_str: Optional[str]) -> FileUploadMetadata:
    """Parse metadata JSON string to FileUploadMetadata."""
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
    background_tasks: BackgroundTasks = None,
):
    """
    Upload a file and process it through the ingestion pipeline.

    This endpoint:
    1. Validates file (size, type)
    2. Uploads file to Azure Blob Storage
    3. Extracts text using FileParserService
    4. Creates document record in Solr
    5. Processes and chunks document for RAG
    6. Logs the upload action

    **Request:**
    - `file`: The file to upload (multipart/form-data)
    - `metadata`: Optional JSON string with document metadata

    **Response:**
    - Document details with processing status and metrics

    **Supported File Types:**
    - PDF (.pdf)
    - Word Documents (.doc, .docx)
    - Text Files (.txt)
    - XML Files (.xml)
    - HTML Files (.html, .htm)

    **Example Metadata:**
    ```json
    {
      "category": "State",
      "state": "CA",
      "tax_year": 2024,
      "jurisdiction": "State",
      "tags": ["sales-tax", "california"]
    }
    ```
    """
    try:
        # Step 1: Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        _validate_file_type(file.filename)

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        _validate_file_size(file_size)

        # Step 2: Parse metadata
        upload_metadata = _parse_metadata(metadata)

        # Step 3: Upload to Azure Blob Storage
        blob_service = get_blob_storage_service()

        if not blob_service.is_configured():
            raise HTTPException(
                status_code=503, detail="Azure Blob Storage is not configured"
            )

        # Generate stored filename (UUID-based for uniqueness)
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

        # Step 4: Create UploadedFile record in PostgreSQL with PENDING status
        uploaded_file_service = UploadedFileService(db)

        try:
            uploaded_file = await uploaded_file_service.create(
                original_filename=file.filename,
                stored_filename=stored_filename,
                file_path=blob_path,
                file_size=file_size,
                mime_type=file.content_type,
                checksum=checksum,
                blob_container=settings.azure_container_uploads,
                blob_path=blob_path,
                blob_url=blob_url,
            )
            uploaded_file_id = str(uploaded_file.id)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create uploaded file record: {str(e)}",
            )

        # Update status to PROCESSING
        await uploaded_file_service.update_processing_status(
            uploaded_file.id, ProcessingStatus.PROCESSING
        )

        # Return immediately with "processing" status - all heavy processing happens in background
        response = FileUploadResponse(
            document_id="pending",  # Will be updated when processing completes
            uploaded_file_id=uploaded_file_id,
            registry_id=None,
            filename=file.filename,
            file_size=file_size,
            blob_path=blob_path,
            blob_url=blob_url,
            content_type=file.content_type or "application/octet-stream",
            status="processing",
            chunks_created=0,
            word_count=0,
            page_count=0,
            parsing_quality=0.0,
            message="File uploaded successfully. Processing in background...",
            document=None,
        )

        # Schedule background processing
        if background_tasks:
            background_tasks.add_task(
                _process_uploaded_file,
                uploaded_file_id=uploaded_file_id,
                file_content=file_content,
                original_filename=file.filename,
                content_type=file.content_type,
                file_size=file_size,
                blob_path=blob_path,
                blob_url=blob_url,
                upload_metadata=upload_metadata,
            )
        else:
            # Fallback: process synchronously if BackgroundTasks not available
            await _process_uploaded_file(
                uploaded_file_id=uploaded_file_id,
                file_content=file_content,
                original_filename=file.filename,
                content_type=file.content_type,
                file_size=file_size,
                blob_path=blob_path,
                blob_url=blob_url,
                upload_metadata=upload_metadata,
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unexpected error during file upload: {str(e)}"
        )


async def _process_uploaded_file(
    uploaded_file_id: str,
    file_content: bytes,
    original_filename: str,
    content_type: str,
    file_size: int,
    blob_path: str,
    blob_url: str,
    upload_metadata: FileUploadMetadata,
):
    """
    Background task to process an uploaded file.

    This handles:
    - Text extraction
    - AI classification
    - Solr document creation
    - Chunking and embedding
    - Status updates
    """
    from ..database.connection import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        uploaded_file_service = UploadedFileService(db)
        extraction_error = None

        try:
            # Step 1: Extract text using FileParserService
            parser_service = get_file_parser_service()

            try:
                # Run CPU-bound file parsing in thread pool to prevent blocking
                parse_result = await asyncio.to_thread(
                    parser_service.extract_text,
                    file_data=file_content,
                    filename=original_filename,
                    mime_type=content_type,
                )
            except Exception as e:
                parse_result = None
                extraction_error = str(e)

            # Step 2: AI Classification
            classification = None
            if parse_result and parse_result.success and parse_result.text:
                try:
                    classifier = get_document_classifier_service(use_ai=True)
                    classification = classifier.classify(
                        text=parse_result.text,
                        source_url=blob_url,
                        filename=original_filename,
                        existing_metadata={
                            "title": upload_metadata.title,
                            "description": upload_metadata.description,
                            "doc_type": upload_metadata.doc_type,
                            "authority_level": upload_metadata.authority_level,
                            "tags": upload_metadata.tags
                            if upload_metadata.tags
                            else None,
                            "tax_year": upload_metadata.tax_year,
                            "form_family": upload_metadata.form_family,
                        },
                    )
                except Exception:
                    classification = None

            # Step 3: Create document record in Solr
            doc_service = get_document_service()

            # Jurisdiction is now required and provided directly by user
            doc_create = DocumentCreate(
                name=original_filename,
                title=upload_metadata.title
                or (classification.title if classification else None)
                or original_filename,
                description=upload_metadata.description
                or (classification.description if classification else None),
                source_url=blob_url,
                source_domain=None,
                tags=upload_metadata.tags
                if upload_metadata.tags
                else (classification.tags if classification else []),
                category=None,  # Deprecated, use jurisdiction instead
                doc_type=upload_metadata.doc_type
                or (classification.doc_type if classification else None),
                tax_year=upload_metadata.tax_year
                or (classification.tax_year if classification else None),
                tax_type=upload_metadata.tax_type,
                jurisdiction=upload_metadata.jurisdiction,  # Directly from user input
                state=upload_metadata.state,
                city=upload_metadata.city,
                authority_level=upload_metadata.authority_level
                or (classification.authority_level if classification else None),
                authority_level_rationale=upload_metadata.authority_level_rationale
                or (
                    classification.authority_level_rationale if classification else None
                ),
                size=str(file_size),
                knowledge_base_id=upload_metadata.knowledge_base_id,
                form_family=upload_metadata.form_family
                or (classification.form_family if classification else None),
                effective_from=datetime.fromisoformat(
                    upload_metadata.effective_from.replace("Z", "+00:00")
                )
                if upload_metadata.effective_from
                else None,
                effective_to=datetime.fromisoformat(
                    upload_metadata.effective_to.replace("Z", "+00:00")
                )
                if upload_metadata.effective_to
                else None,
                applies_to_tax_years=upload_metadata.applies_to_tax_years,
                applies_to_jurisdictions=upload_metadata.applies_to_jurisdictions,
            )

            try:
                document = await doc_service.create_document(doc_create)
            except Exception as e:
                await uploaded_file_service.update_processing_status(
                    uploaded_file_id,
                    ProcessingStatus.FAILED,
                    error=f"Failed to create Solr document: {str(e)}",
                )
                return

            # Link uploaded file to Solr document
            await uploaded_file_service.update_solr_reference(
                uploaded_file_id, document.id
            )

            # Step 4: Create DocumentRegistry entry
            registry_service = DocumentRegistryService(db)
            registry = None

            try:
                registry = await registry_service.create(
                    solr_document_id=document.id,
                    document_name=original_filename,
                    title=upload_metadata.title or original_filename,
                    jurisdiction=upload_metadata.jurisdiction,
                    state=upload_metadata.state,
                    city=upload_metadata.city,
                    tax_year=upload_metadata.tax_year,
                    governance_state="pending",
                    doc_type=upload_metadata.doc_type,
                    category=None,  # Deprecated, use jurisdiction instead
                    source_url=blob_url,
                    uploaded_file_id=uploaded_file_id,
                )

                await registry_service.create_blob(
                    registry_id=registry.id,
                    blob_type="raw",
                    blob_container=settings.azure_container_uploads,
                    blob_path=blob_path,
                    blob_url=blob_url,
                    file_size=file_size,
                    mime_type=content_type,
                    content_hash=None,
                )
            except Exception:
                pass  # Registry creation is optional

            # Step 5: Process and chunk document
            chunks_created = 0
            processing_errors = []

            if parse_result and parse_result.success and parse_result.text:
                try:
                    (
                        chunks_created,
                        errors,
                    ) = await doc_service.process_and_chunk_document(
                        doc_id=document.id,
                        text=parse_result.text,
                        generate_embeddings=True,
                    )
                    if errors:
                        processing_errors.extend(errors)

                    if chunks_created > 0 and registry:
                        await registry_service.update_chunk_count(
                            registry.id, chunks_created
                        )
                except Exception as e:
                    processing_errors.append(str(e))
            elif parse_result and not parse_result.success:
                processing_errors.extend(parse_result.errors)
            elif not parse_result and extraction_error:
                processing_errors.append(extraction_error)

            # Step 6: Update final status
            if chunks_created > 0:
                await uploaded_file_service.update_processing_status(
                    uploaded_file_id, ProcessingStatus.COMPLETED
                )
            else:
                await uploaded_file_service.update_processing_status(
                    uploaded_file_id,
                    ProcessingStatus.FAILED,
                    error="; ".join(processing_errors[:3])
                    if processing_errors
                    else "No chunks created",
                )

            # Step 7: Log audit action
            try:
                audit_service = AuditLogService(db)
                await audit_service.log_action(
                    action="document.upload",
                    resource_type="document",
                    resource_id=document.id,
                    resource_name=original_filename,
                    actor="api",
                    new_values={
                        "filename": original_filename,
                        "file_size": file_size,
                        "blob_path": blob_path,
                        "chunks_created": chunks_created,
                        "uploaded_file_id": uploaded_file_id,
                    },
                    details=f"File processed in background. Chunks: {chunks_created}",
                )
            except Exception:
                pass

        except Exception as e:
            # Mark as failed on any unexpected error
            try:
                await uploaded_file_service.update_processing_status(
                    uploaded_file_id,
                    ProcessingStatus.FAILED,
                    error=f"Background processing failed: {str(e)}",
                )
            except Exception:
                pass
