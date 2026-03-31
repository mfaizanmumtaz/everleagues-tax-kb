"""Shared ingestion pipeline for processing documents from all sources.

Extracted from the per-router background tasks to provide a single, unified
processing path used by:
  - Celery worker tasks (API push, file upload)
  - Web scraper (direct call, keeps sequential flow)
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Tuple
from uuid import UUID

from ..config import settings
from ..database.connection import AsyncSessionLocal
from ..db_models.document_registry import ProcessingStatus
from ..models.document import DocumentCreate
from ..services.blob_storage_service import get_blob_storage_service
from ..services.file_parser import get_file_parser_service
from ..services.document_service import get_document_service
from ..services.document_classifier_service import get_document_classifier_service
from ..services.audit_log_service import AuditLogService
from ..services.document_registry_service import DocumentRegistryService

logger = logging.getLogger(__name__)


async def process_from_registry(
    registry_id: str,
    metadata: Optional[dict] = None,
    source: str = "upload",
    is_replacement: bool = False,
) -> Tuple[bool, int]:
    """Process a document by downloading its content from Azure Blob Storage.

    Used by Celery worker tasks where file content is NOT in memory.
    The file is fetched from blob storage using the DocumentBlob record.

    Args:
        registry_id: UUID string of the DocumentRegistry entry.
        metadata: Optional dict of upload metadata (from FileUploadMetadata).
        source: Source identifier for audit logging ("upload", "api_push").
        is_replacement: Whether this is a file replacement (for audit logging).

    Returns:
        Tuple of (success, chunks_created).
    """
    async with AsyncSessionLocal() as db:
        registry_service = DocumentRegistryService(db)

        # Mark as PROCESSING
        await registry_service.update_processing_status(
            UUID(registry_id), ProcessingStatus.PROCESSING
        )

        # Load registry with blob records
        registry = await registry_service.get_with_blob(UUID(registry_id))
        if not registry:
            logger.error(f"Registry entry not found: {registry_id}")
            return False, 0

        # Find the raw blob record
        raw_blob = None
        for blob in registry.blobs:
            if blob.blob_type == "raw" and blob.is_current:
                raw_blob = blob
                break

        if not raw_blob:
            logger.error(f"No raw blob found for registry: {registry_id}")
            await registry_service.update_processing_status(
                UUID(registry_id),
                ProcessingStatus.FAILED,
                error="No raw blob record found",
            )
            return False, 0

        # Download file content from Azure Blob
        blob_service = get_blob_storage_service()
        file_content = blob_service.download_file(
            container=raw_blob.blob_container,
            blob_path=raw_blob.blob_path,
        )

        if file_content is None:
            logger.error(f"Failed to download blob: {raw_blob.blob_path}")
            await registry_service.update_processing_status(
                UUID(registry_id),
                ProcessingStatus.FAILED,
                error=f"Failed to download file from blob storage: {raw_blob.blob_path}",
            )
            return False, 0

        filename = raw_blob.original_filename or registry.document_name or "unknown"
        content_type = raw_blob.mime_type or "application/octet-stream"
        file_size = raw_blob.file_size or len(file_content)
        blob_url = raw_blob.blob_url or ""

        return await _run_pipeline(
            registry_id=registry_id,
            file_content=file_content,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            source_url=blob_url,
            metadata=metadata,
            source=source,
            is_replacement=is_replacement,
            db=db,
            registry_service=registry_service,
        )


async def process_from_content(
    registry_id: str,
    file_content: bytes,
    filename: str,
    content_type: str,
    metadata: Optional[dict] = None,
    source: str = "scrape",
) -> Tuple[bool, int]:
    """Process a document with file content already in memory.

    Used by the web scraper where file bytes are available from the download step.
    Avoids a redundant Azure Blob download.

    Args:
        registry_id: UUID string of the DocumentRegistry entry.
        file_content: Raw file bytes.
        filename: Original filename.
        content_type: MIME type.
        metadata: Optional dict of metadata for classification context.
        source: Source identifier for audit logging.

    Returns:
        Tuple of (success, chunks_created).
    """
    async with AsyncSessionLocal() as db:
        registry_service = DocumentRegistryService(db)

        return await _run_pipeline(
            registry_id=registry_id,
            file_content=file_content,
            filename=filename,
            content_type=content_type,
            file_size=len(file_content),
            source_url=metadata.get("source_url", "") if metadata else "",
            metadata=metadata,
            source=source,
            is_replacement=False,
            db=db,
            registry_service=registry_service,
        )


async def _run_pipeline(
    registry_id: str,
    file_content: bytes,
    filename: str,
    content_type: str,
    file_size: int,
    source_url: str,
    metadata: Optional[dict],
    source: str,
    is_replacement: bool,
    db,
    registry_service: DocumentRegistryService,
) -> Tuple[bool, int]:
    """Core ingestion pipeline shared by all entry points.

    Steps:
        1. Extract text from file content
        2. Classify document (AI-based, optional)
        3. Build DocumentCreate from metadata + classification
        4. Create Solr document
        5. Link registry to Solr document
        6. Chunk, embed, and index
        7. Update registry status
        8. Write audit log

    Returns:
        Tuple of (success, chunks_created).
    """
    meta = metadata or {}
    extraction_error = None

    try:
        # Step 1: Extract text
        parser_service = get_file_parser_service()
        parse_result = None

        try:
            parse_result = await asyncio.to_thread(
                parser_service.extract_text,
                file_data=file_content,
                filename=filename,
                mime_type=content_type,
            )
            logger.info(f"Text extraction complete: registry_id={registry_id}")
        except Exception as e:
            parse_result = None
            extraction_error = str(e)
            logger.error(f"Text extraction failed: {e}")

        # Step 2: Classify document
        classification = None
        if parse_result and parse_result.success and parse_result.text:
            try:
                classifier = get_document_classifier_service(use_ai=True)
                existing_metadata = {
                    "title": meta.get("title"),
                    "description": meta.get("description"),
                    "doc_type": meta.get("doc_type"),
                    "authority_level": meta.get("authority_level"),
                    "tags": meta.get("tags"),
                    "tax_year": meta.get("tax_year"),
                    "form_family": meta.get("form_family"),
                    "jurisdiction": meta.get("jurisdiction"),
                    "state": meta.get("state"),
                }
                # Remove None values so classifier sees only provided metadata
                existing_metadata = {
                    k: v for k, v in existing_metadata.items() if v is not None
                }
                classification = await asyncio.to_thread(
                    classifier.classify,
                    text=parse_result.text,
                    source_url=source_url,
                    filename=filename,
                    existing_metadata=existing_metadata,
                )
            except Exception:
                classification = None

        # Step 3: Build DocumentCreate
        effective_from = None
        if meta.get("effective_from"):
            try:
                raw = meta["effective_from"]
                effective_from = datetime.fromisoformat(
                    raw.replace("Z", "+00:00") if isinstance(raw, str) else raw
                )
            except Exception:
                effective_from = None

        effective_to = None
        if meta.get("effective_to"):
            try:
                raw = meta["effective_to"]
                effective_to = datetime.fromisoformat(
                    raw.replace("Z", "+00:00") if isinstance(raw, str) else raw
                )
            except Exception:
                effective_to = None

        doc_create = DocumentCreate(
            name=filename,
            title=(
                meta.get("title")
                or (classification.title if classification else None)
                or filename
            ),
            description=(
                meta.get("description")
                or (classification.description if classification else None)
            ),
            source_url=source_url,
            source_domain=meta.get("source_domain"),
            tags=(
                meta.get("tags")
                if meta.get("tags")
                else (classification.tags if classification else [])
            ),
            doc_type=(
                meta.get("doc_type")
                or (classification.doc_type if classification else None)
            ),
            tax_year=(
                meta.get("tax_year")
                or (classification.tax_year if classification else None)
            ),
            tax_type=meta.get("tax_type"),
            jurisdiction=meta.get("jurisdiction"),
            state=meta.get("state"),
            city=meta.get("city"),
            authority_level=(
                meta.get("authority_level")
                or (classification.authority_level if classification else None)
            ),
            authority_level_rationale=(
                meta.get("authority_level_rationale")
                or (
                    classification.authority_level_rationale
                    if classification
                    else None
                )
            ),
            size=str(file_size),
            knowledge_base_id=meta.get("knowledge_base_id", "default"),
            form_family=(
                meta.get("form_family")
                or (classification.form_family if classification else None)
            ),
            effective_from=effective_from,
            effective_to=effective_to,
            applies_to_tax_years=meta.get("applies_to_tax_years", []),
            applies_to_jurisdictions=meta.get("applies_to_jurisdictions", []),
            source_type="api" if source == "api_push" else source,
        )

        # Step 4: Create Solr document
        doc_service = get_document_service()

        try:
            document = await doc_service.create_document(doc_create)
            logger.info(f"Solr document created: document_id={document.id}")
        except Exception as e:
            logger.error(f"Failed to create Solr document: {e}")
            await registry_service.update_processing_status(
                UUID(registry_id),
                ProcessingStatus.FAILED,
                error=f"Failed to create Solr document: {str(e)}",
            )
            return False, 0

        # Step 5: Link registry to Solr document
        await registry_service.update_solr_reference(UUID(registry_id), document.id)

        # Step 6: Chunk + embed + index
        chunks_created = 0
        processing_errors = []

        if parse_result and parse_result.success and parse_result.text:
            try:
                chunks_created, errors = await doc_service.process_and_chunk_document(
                    doc_id=document.id,
                    text=parse_result.text,
                    generate_embeddings=True,
                )
                logger.info(f"Chunking complete: chunks_created={chunks_created}")
                if errors:
                    processing_errors.extend(errors)
                    logger.warning(f"Chunking had errors: {errors[:3]}")

                if chunks_created > 0:
                    await registry_service.update_chunk_count(
                        UUID(registry_id), chunks_created
                    )
            except Exception as e:
                logger.error(f"Chunking failed: {e}")
                processing_errors.append(str(e))
        elif parse_result and not parse_result.success:
            processing_errors.extend(parse_result.errors)
        elif not parse_result and extraction_error:
            processing_errors.append(extraction_error)

        # Step 7: Update registry status
        if chunks_created > 0:
            await registry_service.update_processing_status(
                UUID(registry_id), ProcessingStatus.COMPLETED
            )
            logger.info(
                f"Processing completed successfully: registry_id={registry_id}"
            )
        else:
            error_msg = (
                "; ".join(processing_errors[:3])
                if processing_errors
                else "No chunks created"
            )
            logger.error(f"Processing failed: {error_msg}")
            await registry_service.update_processing_status(
                UUID(registry_id),
                ProcessingStatus.FAILED,
                error=error_msg,
            )

        # Step 8: Audit log
        try:
            audit_service = AuditLogService(db)

            action = f"document.{source}"
            if is_replacement:
                action = "document.api_replace"

            audit_details = {
                "filename": filename,
                "file_size": file_size,
                "chunks_created": chunks_created,
                "registry_id": registry_id,
                "source": source,
            }
            if is_replacement:
                audit_details["is_replacement"] = True

            await audit_service.log_action(
                action=action,
                resource_type="document",
                resource_id=document.id,
                resource_name=filename,
                actor=f"{source}_service",
                new_values=audit_details,
                details=f"File processed via {source}. Chunks: {chunks_created}",
            )
        except Exception:
            pass

        return chunks_created > 0, chunks_created

    except Exception as e:
        logger.exception(f"Ingestion pipeline failed: {e}")
        try:
            await registry_service.update_processing_status(
                UUID(registry_id),
                ProcessingStatus.FAILED,
                error=f"Ingestion pipeline failed: {str(e)}",
            )
        except Exception:
            pass
        return False, 0
