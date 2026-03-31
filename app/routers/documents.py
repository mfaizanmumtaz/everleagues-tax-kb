"""Document API routes."""

import logging
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentListResponse,
    GovernanceStateUpdate,
    ReprocessResponse,
    BulkReprocessResponse,
)
from ..models.common import FilterParams, GovernanceState
from ..services.document_service import get_document_service
from ..services.document_registry_service import DocumentRegistryService
from ..services.audit_log_service import AuditLogService
from ..database.connection import get_db
from ..worker.tasks import process_document
from ..db_models.document_registry import ProcessingStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    query: str = Query(default="*:*", description="Search query"),
    jurisdiction: Optional[str] = Query(
        default=None, description="Filter by jurisdiction"
    ),
    state: Optional[str] = Query(default=None, description="Filter by state"),
    city: Optional[str] = Query(default=None, description="Filter by city"),
    tax_year: Optional[int] = Query(default=None, description="Filter by tax year"),
    authority_level: Optional[int] = Query(
        default=None, ge=1, le=6, description="Filter by authority level"
    ),
    governance_state: Optional[GovernanceState] = Query(
        default=None, description="Filter by governance state"
    ),
    doc_type: Optional[str] = Query(
        default=None, description="Filter by document type"
    ),
    needs_human_review: Optional[bool] = Query(
        default=None, description="Filter by review status"
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    sort: str = Query(
        default="uploadedDate desc", description="Sort field and direction"
    ),
):
    """
    List documents with filters and pagination.

    Returns paginated list of documents matching the filters.
    """
    try:
        service = get_document_service()

        filters = FilterParams(
            jurisdiction=jurisdiction,
            state=state,
            city=city,
            tax_year=tax_year,
            authority_level=authority_level,
            governance_state=governance_state,
            doc_type=doc_type,
            needs_human_review=needs_human_review,
        )

        docs, total = await service.list_documents(
            query=query,
            filters=filters,
            page=page,
            limit=limit,
            sort=sort,
        )

        pages = (total + limit - 1) // limit

        return DocumentListResponse(
            items=docs,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str = Path(..., description="Document ID"),
):
    """
    Get a single document by ID.

    Returns full document details including history.
    """
    try:
        service = get_document_service()
        doc = await service.get_document(document_id)

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(document: DocumentCreate):
    """
    Create a new document.

    Returns the created document.
    """
    try:
        service = get_document_service()
        doc = await service.create_document(document)
        return doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str = Path(..., description="Document ID"),
    updates: DocumentUpdate = ...,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a document.

    Returns the updated document.
    """
    try:
        service = get_document_service()

        # Get current document for audit log (old values)
        existing = await service.get_document(document_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Document not found")

        # Capture old values for changed fields
        update_data = updates.model_dump(exclude_unset=True)
        old_values = {}
        for field_name in update_data:
            old_val = getattr(existing, field_name, None)
            if old_val is not None:
                old_values[field_name] = str(old_val) if not isinstance(old_val, (str, int, float, bool, list)) else old_val
            else:
                old_values[field_name] = None

        doc = await service.update_document(document_id, updates)

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Audit log: document metadata updated
        try:
            audit_service = AuditLogService(db)
            await audit_service.log_document_update(
                document_id=document_id,
                document_name=existing.name,
                old_values=old_values,
                new_values=update_data,
            )
        except Exception:
            pass  # Don't fail the request if audit logging fails

        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str = Path(..., description="Document ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a document and all its chunks.
    """
    try:
        service = get_document_service()

        doc = await service.get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Capture name before deletion for audit log
        doc_name = doc.name

        await service.delete_document(document_id)

        registry_service = DocumentRegistryService(db)
        await registry_service.delete_by_solr_id(document_id)

        # Audit log: document deleted
        try:
            audit_service = AuditLogService(db)
            await audit_service.log_document_delete(
                document_id=document_id,
                document_name=doc_name,
            )
        except Exception:
            pass  # Don't fail the request if audit logging fails
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str = Path(..., description="Document ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=100, ge=1, le=1000, description="Items per page"),
):
    """
    Get all chunks for a document.

    Returns paginated list of chunks belonging to the document.
    """
    try:
        service = get_document_service()

        # Check if document exists
        doc = await service.get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        chunks, total = await service.get_document_chunks(
            document_id, page=page, limit=limit
        )

        pages = (total + limit - 1) // limit

        return {
            "items": chunks,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{document_id}/governance", response_model=DocumentResponse)
async def update_governance_state(
    document_id: str = Path(..., description="Document ID"),
    update: GovernanceStateUpdate = ...,
):
    """
    Update document governance state.

    Adds an entry to the governance history.
    """
    try:
        service = get_document_service()
        doc = await service.update_governance_state(document_id, update)

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{document_id}/reprocess", response_model=ReprocessResponse)
async def reprocess_document(
    document_id: str = Path(..., description="Document ID (Solr ID)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Reprocess a failed document.

    Re-queues the document for processing through the ingestion pipeline.
    The document must have a failed status (sync_failed or index_failed).
    """
    try:
        doc_service = get_document_service()
        registry_service = DocumentRegistryService(db)

        # Get the Solr document to check status
        doc = await doc_service.get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Check if document is in failed state
        is_failed = (
            doc.sync_status.value == "sync_failed"
            or doc.index_status.value == "index_failed"
        )
        if not is_failed:
            return ReprocessResponse(
                registry_id="",
                status="not_failed",
                message="Document is not in failed state.",
            )

        # Get registry entry with blob
        registry = await registry_service.get_by_solr_id_with_blob(document_id)
        if not registry:
            return ReprocessResponse(
                registry_id="",
                status="not_found",
                message="Document registry entry not found. Cannot reprocess.",
            )

        # Check if already processing
        if registry.processing_status == ProcessingStatus.PROCESSING:
            return ReprocessResponse(
                registry_id=str(registry.id),
                status="already_processing",
                message="Document is already being processed.",
            )

        # Check for raw blob
        raw_blob = None
        for blob in registry.blobs:
            if blob.blob_type == "raw" and blob.is_current:
                raw_blob = blob
                break

        if not raw_blob:
            return ReprocessResponse(
                registry_id=str(registry.id),
                status="no_blob_found",
                message="No raw file blob found. Cannot reprocess without source file.",
            )

        # Delete existing Solr document and chunks before reprocessing
        await doc_service.delete_document(document_id)

        # Clear the solr_document_id since we deleted the Solr doc
        registry.solr_document_id = None
        await db.commit()

        # Reset registry status and queue for reprocessing
        await registry_service.reset_for_reprocess(registry.id)

        # Build metadata from registry for reprocessing
        metadata = {
            "title": registry.title,
            "jurisdiction": registry.jurisdiction,
            "state": registry.state,
            "city": registry.city,
            "tax_year": registry.tax_year,
            "doc_type": registry.doc_type,
        }

        # Determine source type
        source = registry.source_type.value if registry.source_type else "upload"

        # Queue the Celery task
        process_document.delay(
            registry_id=str(registry.id),
            metadata=metadata,
            source=source,
            is_replacement=False,
        )

        logger.info(f"Document reprocess queued: document_id={document_id}, registry_id={registry.id}")

        # Update Solr status to show reprocessing (will be overwritten by worker)
        # This provides immediate UI feedback

        return ReprocessResponse(
            registry_id=str(registry.id),
            status="queued",
            message="Document queued for reprocessing.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to reprocess document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reprocess-failed", response_model=BulkReprocessResponse)
async def reprocess_all_failed(
    db: AsyncSession = Depends(get_db),
):
    """
    Reprocess all failed documents.

    Finds all documents with sync_failed or index_failed status
    and queues them for reprocessing.
    """
    try:
        doc_service = get_document_service()
        registry_service = DocumentRegistryService(db)

        # Query Solr for failed documents
        failed_docs, total = await doc_service.list_documents(
            query="syncStatus:sync_failed OR indexStatus:index_failed",
            page=1,
            limit=1000,  # Process up to 1000 at a time
        )

        if not failed_docs:
            return BulkReprocessResponse(
                queued_count=0,
                skipped_count=0,
                failed_ids=[],
                message="No failed documents found.",
            )

        queued_count = 0
        skipped_count = 0
        failed_ids = []

        for doc in failed_docs:
            try:
                # Get registry entry with blob
                registry = await registry_service.get_by_solr_id_with_blob(doc.id)
                if not registry:
                    skipped_count += 1
                    failed_ids.append(doc.id)
                    continue

                # Skip if already processing
                if registry.processing_status == ProcessingStatus.PROCESSING:
                    skipped_count += 1
                    continue

                # Check for raw blob
                raw_blob = None
                for blob in registry.blobs:
                    if blob.blob_type == "raw" and blob.is_current:
                        raw_blob = blob
                        break

                if not raw_blob:
                    skipped_count += 1
                    failed_ids.append(doc.id)
                    continue

                # Delete existing Solr document and chunks
                await doc_service.delete_document(doc.id)

                # Clear the solr_document_id
                registry.solr_document_id = None
                await db.commit()

                # Reset registry status
                await registry_service.reset_for_reprocess(registry.id)

                # Build metadata
                metadata = {
                    "title": registry.title,
                    "jurisdiction": registry.jurisdiction,
                    "state": registry.state,
                    "city": registry.city,
                    "tax_year": registry.tax_year,
                    "doc_type": registry.doc_type,
                }

                source = registry.source_type.value if registry.source_type else "upload"

                # Queue the Celery task
                process_document.delay(
                    registry_id=str(registry.id),
                    metadata=metadata,
                    source=source,
                    is_replacement=False,
                )

                queued_count += 1

            except Exception as e:
                logger.warning(f"Failed to queue reprocess for document {doc.id}: {e}")
                skipped_count += 1
                failed_ids.append(doc.id)

        logger.info(
            f"Bulk reprocess completed: queued={queued_count}, skipped={skipped_count}"
        )

        return BulkReprocessResponse(
            queued_count=queued_count,
            skipped_count=skipped_count,
            failed_ids=failed_ids,
            message=f"{queued_count} document(s) queued for reprocessing.",
        )

    except Exception as e:
        logger.exception(f"Failed to bulk reprocess documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
