"""File Upload API routes."""

import json
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from ..config import settings
from ..models.upload import FileUploadMetadata, FileUploadResponse
from ..models.document import DocumentCreate
from ..database.connection import get_db
from ..services.blob_storage_service import get_blob_storage_service
from ..services.file_parser import get_file_parser_service
from ..services.document_service import get_document_service
from ..services.audit_log_service import AuditLogService

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
    background_tasks: Optional[BackgroundTasks] = None,
    db: Session = Depends(get_db),
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
        
        try:
            blob_path, blob_url, checksum, stored_size = blob_service.upload_file(
                container=settings.azure_container_uploads,
                file_data=file_content,
                filename=file.filename,
                folder=None,
                metadata={
                    "upload_source": "api",
                    "content_type": file.content_type or "application/octet-stream",
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store file in blob storage: {str(e)}"
            )
        
        # Step 4: Extract text using FileParserService
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
        
        # Step 5: Create document record
        doc_service = get_document_service()
        
        # Build DocumentCreate from metadata and file info
        doc_create = DocumentCreate(
            name=file.filename,
            title=upload_metadata.title or file.filename,
            description=upload_metadata.description,
            source_url=blob_url,
            source_domain=None,  # File uploads don't have a domain
            tags=upload_metadata.tags,
            category=upload_metadata.category,
            doc_type=upload_metadata.doc_type,
            tax_year=upload_metadata.tax_year,
            tax_type=upload_metadata.tax_type,
            jurisdiction=upload_metadata.jurisdiction,
            state=upload_metadata.state,
            city=upload_metadata.city,
            authority_level=upload_metadata.authority_level,
            authority_level_rationale=upload_metadata.authority_level_rationale,
            size=str(file_size),
            knowledge_base_id=upload_metadata.knowledge_base_id,
        )
        
        try:
            document = doc_service.create_document(doc_create)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create document record: {str(e)}"
            )
        
        # Step 6: Process and chunk document if extraction succeeded
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
        
        # Step 7: Log audit action
        try:
            audit_service = AuditLogService(db)
            audit_service.log_action(
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
                },
                details=f"File uploaded via API. Status: {status}. Chunks: {chunks_created}",
            )
        except Exception as e:
            # Don't fail the upload if audit logging fails
            pass
        
        # Step 8: Refresh document to get latest status
        try:
            document = doc_service.get_document(document.id)
        except Exception:
            pass
        
        # Build response
        response = FileUploadResponse(
            document_id=document.id,
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
