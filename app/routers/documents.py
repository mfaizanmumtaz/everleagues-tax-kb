"""Document API routes."""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentListResponse,
    GovernanceStateUpdate,
)
from ..models.common import FilterParams, GovernanceState
from ..services.document_service import get_document_service
from ..services.document_registry_service import DocumentRegistryService
from ..services.audit_log_service import AuditLogService
from ..database.connection import get_db

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
    category: Optional[List[str]] = Query(
        default=None, description="Filter by category"
    ),
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
            category=category,
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
