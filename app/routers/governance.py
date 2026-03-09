"""Governance API routes."""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.common import GovernanceState
from ..services.document_service import get_document_service
from ..services.solr_service import get_solr_service
from ..services.audit_log_service import AuditLogService
from ..database.connection import get_db

# Import Pydantic models from models directory
from ..models.governance import (
    GovernanceLogEntry,
    GovernanceLogsResponse,
    GovernanceLogCreate,
)

router = APIRouter(prefix="/governance", tags=["Governance"])


@router.get("/logs", response_model=GovernanceLogsResponse)
async def get_governance_logs(
    document_id: Optional[str] = Query(
        default=None, description="Filter by document ID"
    ),
    from_state: Optional[GovernanceState] = Query(
        default=None, description="Filter by from state"
    ),
    to_state: Optional[GovernanceState] = Query(
        default=None, description="Filter by to state"
    ),
    changed_by: Optional[str] = Query(default=None, description="Filter by user"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    """
    Get governance audit logs.

    Returns paginated list of governance state changes.
    """
    try:
        solr = get_solr_service()
        document_service = get_document_service()

        # Build filters
        filters = []
        if document_id:
            filters.append(f"id:{document_id}")
        if to_state:
            filters.append(f'governanceState:"{to_state.value}"')

        # Get documents that have governance history
        # Note: do NOT sort by updatedAt here -- the field lacks docValues in Solr.
        # We sort the extracted log entries in Python below instead.
        docs, total = await solr.search_documents(
            query="governanceHistory:*",
            filters=filters if filters else None,
            start=(page - 1) * limit,
            rows=limit,
        )

        # Extract governance log entries from documents
        log_entries = []
        for doc in docs:
            doc_response = document_service._solr_to_response(doc)

            for history_entry in doc_response.governance_history:
                # Apply filters
                if from_state and history_entry.from_state != from_state.value:
                    continue
                if changed_by and history_entry.changed_by != changed_by:
                    continue

                log_entries.append(
                    GovernanceLogEntry(
                        id=f"{doc['id']}_{history_entry.timestamp.isoformat()}",
                        document_id=doc["id"],
                        document_name=doc.get("name", doc.get("documentName", "")),
                        from_state=history_entry.from_state,
                        to_state=history_entry.to_state,
                        changed_by=history_entry.changed_by,
                        reason=history_entry.reason,
                        timestamp=history_entry.timestamp,
                    )
                )

        # Sort by timestamp descending
        log_entries.sort(key=lambda x: x.timestamp, reverse=True)

        # Paginate
        total_entries = len(log_entries)
        pages = (total_entries + limit - 1) // limit

        return GovernanceLogsResponse(
            items=log_entries[:limit],
            total=total_entries,
            page=page,
            limit=limit,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logs", response_model=GovernanceLogEntry, status_code=201)
async def create_governance_log(
    entry: GovernanceLogCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a governance log entry by updating a document's governance state.

    This updates the document's governance state and adds a history entry.
    """
    try:
        from ..models.document import GovernanceStateUpdate

        document_service = get_document_service()
        audit_service = AuditLogService(db)

        # Check if document exists
        doc = await document_service.get_document(entry.document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Store previous state for audit log
        previous_state = (
            doc.governance_state.value
            if hasattr(doc.governance_state, "value")
            else str(doc.governance_state)
        )

        # Update governance state
        update = GovernanceStateUpdate(
            governance_state=entry.to_state,
            changed_by=entry.changed_by,
            reason=entry.reason,
        )

        updated_doc = await document_service.update_governance_state(
            entry.document_id, update
        )

        # Log to PostgreSQL audit log
        await audit_service.log_governance_change(
            document_id=entry.document_id,
            document_name=updated_doc.name,
            from_state=previous_state,
            to_state=entry.to_state.value,
            actor=entry.changed_by,
            reason=entry.reason,
        )

        # Return the new log entry
        if updated_doc.governance_history:
            latest = updated_doc.governance_history[-1]
            return GovernanceLogEntry(
                id=f"{entry.document_id}_{latest.timestamp.isoformat()}",
                document_id=entry.document_id,
                document_name=updated_doc.name,
                from_state=latest.from_state,
                to_state=latest.to_state,
                changed_by=latest.changed_by,
                reason=latest.reason,
                timestamp=latest.timestamp,
            )

        # Fallback
        return GovernanceLogEntry(
            id=f"{entry.document_id}_{datetime.utcnow().isoformat()}",
            document_id=entry.document_id,
            document_name=updated_doc.name,
            from_state=previous_state,
            to_state=entry.to_state.value,
            changed_by=entry.changed_by,
            reason=entry.reason,
            timestamp=datetime.utcnow(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/{document_id}", response_model=List[GovernanceLogEntry])
async def get_document_governance_logs(
    document_id: str = Path(..., description="Document ID"),
):
    """
    Get governance logs for a specific document.

    Returns all governance history entries for the document.
    """
    try:
        document_service = get_document_service()

        doc = await document_service.get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        log_entries = []
        for history_entry in doc.governance_history:
            log_entries.append(
                GovernanceLogEntry(
                    id=f"{document_id}_{history_entry.timestamp.isoformat()}",
                    document_id=document_id,
                    document_name=doc.name,
                    from_state=history_entry.from_state,
                    to_state=history_entry.to_state,
                    changed_by=history_entry.changed_by,
                    reason=history_entry.reason,
                    timestamp=history_entry.timestamp,
                )
            )

        # Sort by timestamp descending
        log_entries.sort(key=lambda x: x.timestamp, reverse=True)

        return log_entries
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
