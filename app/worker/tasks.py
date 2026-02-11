"""Celery task definitions for the document ingestion pipeline."""

import asyncio
import logging
from typing import Optional

from celery.exceptions import SoftTimeLimitExceeded

from .celery_app import celery_app
from ..config import settings

logger = logging.getLogger(__name__)

# Reusable event loop for the worker process.
# Avoids creating/destroying a loop (and its DB connection pools) per task.
_loop: Optional[asyncio.AbstractEventLoop] = None


def _get_loop() -> asyncio.AbstractEventLoop:
    """Get or create a persistent event loop for this worker process."""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop


@celery_app.task(
    bind=True,
    max_retries=settings.worker_max_retries,
    default_retry_delay=settings.worker_retry_delay,
    acks_late=True,
)
def process_document(
    self,
    registry_id: str,
    metadata: Optional[dict] = None,
    source: str = "upload",
    is_replacement: bool = False,
):
    """Celery task that processes a document through the ingestion pipeline.

    The file content is fetched from Azure Blob Storage using the
    DocumentBlob record linked to the given registry_id.  No large
    binary payloads pass through Redis.

    Args:
        registry_id: UUID string of the DocumentRegistry entry.
        metadata: Serialized upload metadata dict (from FileUploadMetadata).
        source: Origin identifier -- "upload", "api_push".
        is_replacement: True when replacing an existing API-pushed file.
    """
    logger.info(
        f"Celery task started: registry_id={registry_id}, source={source}, "
        f"attempt={self.request.retries + 1}/{self.max_retries + 1}"
    )

    loop = _get_loop()

    try:
        from ..services.ingestion_service import process_from_registry

        success, chunks = loop.run_until_complete(
            process_from_registry(
                registry_id=registry_id,
                metadata=metadata,
                source=source,
                is_replacement=is_replacement,
            )
        )

        if success:
            logger.info(
                f"Celery task completed: registry_id={registry_id}, "
                f"chunks={chunks}"
            )
        else:
            logger.warning(
                f"Celery task finished with failure: registry_id={registry_id}"
            )

        return {"registry_id": registry_id, "success": success, "chunks": chunks}

    except SoftTimeLimitExceeded:
        logger.error(
            f"Celery task timed out: registry_id={registry_id}"
        )
        try:
            loop.run_until_complete(
                _mark_failed(registry_id, "Task timed out (soft time limit exceeded)")
            )
        except Exception:
            pass
        return {
            "registry_id": registry_id,
            "success": False,
            "error": "Task timed out",
        }

    except Exception as exc:
        logger.exception(
            f"Celery task error: registry_id={registry_id}, error={exc}"
        )

        # If retries are exhausted, mark the document as permanently failed
        if self.request.retries >= self.max_retries:
            logger.error(
                f"Max retries exhausted for registry_id={registry_id}. "
                "Marking as FAILED."
            )
            try:
                loop.run_until_complete(_mark_failed(registry_id, str(exc)))
            except Exception:
                pass
            return {
                "registry_id": registry_id,
                "success": False,
                "error": str(exc),
            }

        raise self.retry(exc=exc)


async def _mark_failed(registry_id: str, error: str) -> None:
    """Helper to mark a registry entry as FAILED from sync context."""
    from uuid import UUID
    from ..database.connection import AsyncSessionLocal
    from ..services.document_registry_service import DocumentRegistryService
    from ..db_models.document_registry import ProcessingStatus

    async with AsyncSessionLocal() as db:
        service = DocumentRegistryService(db)
        await service.update_processing_status(
            UUID(registry_id),
            ProcessingStatus.FAILED,
            error=f"Processing failed after retries: {error}",
        )
