"""File Upload API routes."""

import json
import os
from typing import Optional
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Depends
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
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb}MB"
        )


def _validate_file_type(filename: str) -> None:
    """Validate file extension is in allowed list."""
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    if ext not in settings.allowed_file_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported types: {', '.join(settings.allowed_file_extensions)}"
        )


def _parse_metadata(metadata_str: Optional[str]) -> FileUploadMetadata:
    """Parse metadata JSON string to FileUploadMetadata."""
    if not metadata_str:
        return FileUploadMetadata()
    
    try:
        metadata_dict = json.loads(metadata_str)
        return FileUploadMetadata(**metadata_dict)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metadata JSON: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error parsing metadata: {str(e)}"
        )


@router.post("", response_model=FileUploadResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    metadata: str = Form(None, description="JSON string with document metadata"),
    db: AsyncSession = Depends(get_db),
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
                status_code=503,
                detail="Azure Blob Storage is not configured"
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
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store file in blob storage: {str(e)}"
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
                detail=f"Failed to create uploaded file record: {str(e)}"
            )
        
        # Update status to PROCESSING
        await uploaded_file_service.update_processing_status(
            uploaded_file.id,
            ProcessingStatus.PROCESSING
        )
        
        # Step 5: Extract text using FileParserService
        parser_service = get_file_parser_service()
        
        try:
            parse_result = parser_service.extract_text(
                file_data=file_content,
                filename=file.filename,
                mime_type=file.content_type,
            )
        except Exception as e:
            # Still create document record even if extraction fails
            parse_result = None
            extraction_error = str(e)
        
        # Step 6: AI Classification - Auto-extract metadata from document content
        classification = None
        if parse_result and parse_result.success and parse_result.text:
            try:
                classifier = get_document_classifier_service(use_ai=True)
                classification = classifier.classify(
                    text=parse_result.text,
                    source_url=blob_url,
                    filename=file.filename,
                    existing_metadata={
                        "title": upload_metadata.title,
                        "description": upload_metadata.description,
                        "doc_type": upload_metadata.doc_type,
                        "authority_level": upload_metadata.authority_level,
                        "tags": upload_metadata.tags if upload_metadata.tags else None,
                        "tax_year": upload_metadata.tax_year,
                        "form_family": upload_metadata.form_family,
                    }
                )
            except Exception as e:
                # Classification is optional - continue without it
                classification = None
        
        # Step 7: Create document record in Solr
        doc_service = get_document_service()
        
        # Auto-derive jurisdiction from category or AI classification
        derived_jurisdiction = None
        if upload_metadata.category:
            category_lower = upload_metadata.category.lower()
            if category_lower in ("federal", "state", "local"):
                derived_jurisdiction = category_lower
        elif classification and classification.jurisdiction:
            derived_jurisdiction = classification.jurisdiction
        
        # Build DocumentCreate from metadata, AI classification, and file info
        # Priority: User-provided metadata > AI classification > defaults
        doc_create = DocumentCreate(
            name=file.filename,
            title=upload_metadata.title or (classification.title if classification else None) or file.filename,
            description=upload_metadata.description or (classification.description if classification else None),
            source_url=blob_url,
            source_domain=None,  # File uploads don't have a domain
            tags=upload_metadata.tags if upload_metadata.tags else (classification.tags if classification else []),
            category=upload_metadata.category,
            doc_type=upload_metadata.doc_type or (classification.doc_type if classification else None),
            tax_year=upload_metadata.tax_year or (classification.tax_year if classification else None),
            tax_type=upload_metadata.tax_type,
            jurisdiction=derived_jurisdiction,
            state=upload_metadata.state,
            city=upload_metadata.city,
            authority_level=upload_metadata.authority_level or (classification.authority_level if classification else None),
            authority_level_rationale=upload_metadata.authority_level_rationale or (classification.authority_level_rationale if classification else None),
            size=str(file_size),
            knowledge_base_id=upload_metadata.knowledge_base_id,
            
            # New fields
            form_family=upload_metadata.form_family or (classification.form_family if classification else None),
            effective_from=datetime.fromisoformat(upload_metadata.effective_from.replace('Z', '+00:00')) if upload_metadata.effective_from else None,
            effective_to=datetime.fromisoformat(upload_metadata.effective_to.replace('Z', '+00:00')) if upload_metadata.effective_to else None,
            applies_to_tax_years=upload_metadata.applies_to_tax_years,
            applies_to_jurisdictions=upload_metadata.applies_to_jurisdictions,
        )
        
        try:
            document = doc_service.create_document(doc_create)
        except Exception as e:
            # Mark uploaded file as failed
            await uploaded_file_service.update_processing_status(
                uploaded_file.id,
                ProcessingStatus.FAILED,
                error=f"Failed to create Solr document: {str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create document record: {str(e)}"
            )
        
        # Link uploaded file to Solr document
        await uploaded_file_service.update_solr_reference(uploaded_file.id, document.id)
        
        # Step 7: Create DocumentRegistry entry in PostgreSQL
        registry_service = DocumentRegistryService(db)
        registry_id = None
        
        try:
            registry = await registry_service.create(
                solr_document_id=document.id,
                document_name=file.filename,
                title=upload_metadata.title or file.filename,
                jurisdiction=upload_metadata.jurisdiction,
                state=upload_metadata.state,
                city=upload_metadata.city,
                tax_year=upload_metadata.tax_year,
                governance_state="pending",  # Initial governance state
                doc_type=upload_metadata.doc_type,
                category=upload_metadata.category,
                source_url=blob_url,
                uploaded_file_id=uploaded_file.id,
            )
            registry_id = str(registry.id)

            # Create blob reference for the raw file
            await registry_service.create_blob(
                registry_id=registry.id,
                blob_type="raw",
                blob_container=settings.azure_container_uploads,
                blob_path=blob_path,
                blob_url=blob_url,
                file_size=file_size,
                mime_type=file.content_type,
                content_hash=checksum,
            )
        except Exception as e:
            # Don't fail the upload if registry creation fails - log and continue
            registry_id = None
        
        # Step 8: Process and chunk document if extraction succeeded
        chunks_created = 0
        status = "uploaded"
        message = "File uploaded successfully"
        processing_errors = []
        
        if parse_result and parse_result.success and parse_result.text:
            try:
                chunks_created, errors = doc_service.process_and_chunk_document(
                    doc_id=document.id,
                    text=parse_result.text,
                    generate_embeddings=True,
                )

                if errors:
                    processing_errors.extend(errors)

                if chunks_created > 0:
                    status = "indexed"
                    message = f"File uploaded and indexed successfully. Created {chunks_created} chunks."

                    # Update registry chunk count
                    if registry_id:
                        await registry_service.update_chunk_count(registry.id, chunks_created)
                else:
                    status = "processing"
                    message = "File uploaded but chunking failed or produced no chunks."
                    if errors:
                        message += f" Errors: {'; '.join(errors[:3])}"
            except Exception as e:
                status = "failed"
                message = f"File uploaded but processing failed: {str(e)}"
                processing_errors.append(str(e))
        elif parse_result and not parse_result.success:
            status = "failed"
            message = f"File uploaded but text extraction failed: {'; '.join(parse_result.errors[:3])}"
            processing_errors.extend(parse_result.errors)
        elif not parse_result:
            status = "failed"
            message = f"File uploaded but text extraction failed: {extraction_error}"
            processing_errors.append(extraction_error)
        
        # Step 9: Update uploaded file processing status
        if status == "indexed":
            await uploaded_file_service.update_processing_status(
                uploaded_file.id,
                ProcessingStatus.COMPLETED
            )
        elif status == "failed":
            await uploaded_file_service.update_processing_status(
                uploaded_file.id,
                ProcessingStatus.FAILED,
                error="; ".join(processing_errors[:3]) if processing_errors else "Unknown error"
            )
        
        # Step 10: Log audit action
        try:
            audit_service = AuditLogService(db)
            await audit_service.log_action(
                action="document.upload",
                resource_type="document",
                resource_id=document.id,
                resource_name=file.filename,
                actor="api",  # Could be enhanced with user authentication
                new_values={
                    "filename": file.filename,
                    "file_size": file_size,
                    "blob_path": blob_path,
                    "chunks_created": chunks_created,
                    "word_count": parse_result.word_count if parse_result else 0,
                    "status": status,
                    "uploaded_file_id": uploaded_file_id,
                    "registry_id": registry_id,
                },
                details=f"File uploaded via API. Status: {status}. Chunks: {chunks_created}",
            )
        except Exception as e:
            # Don't fail the upload if audit logging fails
            pass
        
        # Step 11: Refresh document to get latest status
        try:
            document = doc_service.get_document(document.id)
        except Exception:
            pass
        
        # Build response
        response = FileUploadResponse(
            document_id=document.id,
            uploaded_file_id=uploaded_file_id,
            registry_id=registry_id,
            filename=file.filename,
            file_size=file_size,
            blob_path=blob_path,
            blob_url=blob_url,
            content_type=file.content_type or "application/octet-stream",
            status=status,
            chunks_created=chunks_created,
            word_count=parse_result.word_count if parse_result else 0,
            page_count=parse_result.page_count if parse_result else 0,
            parsing_quality=parse_result.parsing_quality if parse_result else 0.0,
            message=message,
            document=document,
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during file upload: {str(e)}"
        )
