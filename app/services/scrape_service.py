"""Scrape execution service -- downloads approved pages and processes through ingestion pipeline."""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID, uuid4
from urllib.parse import urlparse

import httpx
import redis as redis_lib

from ..config import settings
from ..database.connection import AsyncSessionLocal
from ..db_models.scrape_job import LogLevel
from ..services.scrape_job_service import ScrapeJobService
from ..services.discovered_page_service import DiscoveredPageService
from ..services.url_db_service import UrlDbService
from ..services.document_registry_service import DocumentRegistryService
from ..services.blob_storage_service import get_blob_storage_service
from ..services.ingestion_service import process_from_content
from ..services.audit_log_service import AuditLogService
from ..db_models.document_registry import ProcessingStatus
from ..db_models.scrape_url import UrlStatus

logger = logging.getLogger(__name__)

_redis_client: Optional[redis_lib.Redis] = None


def _get_redis() -> redis_lib.Redis:
    """Get or create a Redis client for cancellation checks."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.Redis.from_url(
            settings.celery_broker_url, decode_responses=True
        )
    return _redis_client

# File extensions considered as downloadable documents
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".csv", ".rtf"}

# Content types mapped to file extensions for HTML pages
CONTENT_TYPE_EXTENSIONS = {
    "text/html": ".html",
    "text/plain": ".txt",
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


async def run_scrape(
    scrape_url_id: str,
    job_id: str,
    cancel_key: str,
) -> None:
    """
    Main scrape execution function. Runs as a Celery task with its own DB session.

    Downloads all approved pages for the given URL, processes each through the
    full ingestion pipeline (blob storage, parse, classify, chunk, embed, Solr index).

    Args:
        scrape_url_id: UUID of the ScrapeUrl to scrape
        job_id: UUID of the ScrapeJob tracking this run
        cancel_key: Redis key to check for cancellation signal
    """
    url_uuid = UUID(scrape_url_id)
    job_uuid = UUID(job_id)
    redis_client = _get_redis()

    # Clear any stale cancel key from a previous run
    redis_client.delete(cancel_key)

    async with AsyncSessionLocal() as db:
        job_service = ScrapeJobService(db)
        page_service = DiscoveredPageService(db)
        url_service = UrlDbService(db)
        registry_service = DocumentRegistryService(db)
        audit_service = AuditLogService(db)

        documents_created = 0
        documents_failed = 0
        total_chunks = 0

        try:
            # Mark job as running
            await job_service.start_job(job_uuid)
            await job_service.add_log(job_uuid, LogLevel.INFO, "Scrape job started")

            # Get scrape URL config for rate limiting
            scrape_url = await url_service.get_url(url_uuid)
            if not scrape_url:
                await job_service.fail_job(job_uuid, "Scrape URL not found")
                return

            delay = scrape_url.delay_between_requests or 2
            max_files = scrape_url.max_files_per_session or 10000

            # Update URL status to scraping
            await url_service.update_url_status(url_uuid, UrlStatus.SCRAPING)

            # Get approved pages
            approved_pages = await page_service.get_approved_for_ingestion(url_uuid)
            total_pages = len(approved_pages)

            if total_pages == 0:
                await job_service.add_log(
                    job_uuid, LogLevel.WARNING, "No approved pages found to scrape"
                )
                await job_service.complete_job(job_uuid)
                await url_service.update_url_status(url_uuid, UrlStatus.ACTIVE)
                return

            await job_service.update_progress(
                job_uuid, 0, total_pages, f"Starting scrape of {total_pages} pages"
            )

            # Process each approved page
            for idx, page in enumerate(approved_pages):
                # Check cancellation via Redis key
                if redis_client.exists(cancel_key):
                    redis_client.delete(cancel_key)
                    await job_service.add_log(
                        job_uuid, LogLevel.INFO, "Scrape cancelled by user"
                    )
                    await job_service.cancel_job(job_uuid)
                    await url_service.update_url_status(url_uuid, UrlStatus.ACTIVE)
                    return

                # Check file limit
                if documents_created >= max_files:
                    await job_service.add_log(
                        job_uuid,
                        LogLevel.WARNING,
                        f"File limit reached ({max_files}). Stopping.",
                    )
                    break

                # Update progress
                await job_service.update_progress(
                    job_uuid,
                    idx,
                    total_pages,
                    f"Processing page {idx + 1}/{total_pages}: {page.url[:80]}",
                )

                # Process single page
                success, chunks = await _process_single_page(
                    page=page,
                    scrape_url=scrape_url,
                    job_id=job_uuid,
                    job_service=job_service,
                    registry_service=registry_service,
                )

                if success:
                    documents_created += 1
                    total_chunks += chunks
                    # Mark page as ingested
                    await page_service.mark_as_ingested([page.id])
                else:
                    documents_failed += 1

                # Rate limiting delay between pages
                if idx < total_pages - 1:
                    await asyncio.sleep(delay)

            # Complete job
            await job_service.update_progress(
                job_uuid, total_pages, total_pages, "Scrape completed"
            )
            await job_service.complete_job(
                job_uuid,
                documents_created=documents_created,
                documents_failed=documents_failed,
                chunks_created=total_chunks,
            )

            # Update URL stats
            now = datetime.now(timezone.utc)
            await url_service.update_url_status(url_uuid, UrlStatus.ACTIVE)
            await url_service.update_scrape_stats(
                url_uuid,
                last_scraped_at=now,
                last_successful_at=now if documents_created > 0 else None,
            )
            await url_service.increment_documents_count(url_uuid, documents_created)

            # Audit log
            await audit_service.log_url_scrape(
                url_id=scrape_url_id,
                url=scrape_url.url,
                documents_created=documents_created,
            )

            await job_service.add_log(
                job_uuid,
                LogLevel.INFO,
                f"Scrape completed: {documents_created} created, {documents_failed} failed, {total_chunks} chunks",
            )

        except Exception as e:
            logger.exception("Scrape job failed with unexpected error")
            try:
                await job_service.fail_job(job_uuid, str(e))
                await job_service.add_log(
                    job_uuid, LogLevel.ERROR, f"Scrape failed: {str(e)}"
                )
                await url_service.update_url_status(url_uuid, UrlStatus.ERROR, str(e))
            except Exception:
                pass


async def _process_single_page(
    page,
    scrape_url,
    job_id: UUID,
    job_service: ScrapeJobService,
    registry_service: DocumentRegistryService,
) -> Tuple[bool, int]:
    """
    Process a single discovered page through the full ingestion pipeline.

    Steps 1-4 (download, filename, blob upload, registry creation) happen here.
    Steps 5-9 (extract, classify, Solr, chunk, status update) are delegated to
    the shared ingestion_service.process_from_content().

    Returns:
        Tuple of (success: bool, chunks_created: int)
    """
    try:
        # Step 1: Download the page
        content, content_type, status_code = await _download_page(page.url)
        if content is None:
            await job_service.add_log(
                job_id,
                LogLevel.WARNING,
                f"Failed to download: {page.url} (HTTP {status_code})",
            )
            return False, 0

        # Step 2: Determine filename and extension
        filename, file_ext = _determine_filename(page.url, content_type)

        # Step 3: Upload to Azure Blob Storage
        blob_service = get_blob_storage_service()
        if not blob_service.is_configured():
            await job_service.add_log(
                job_id, LogLevel.ERROR, "Azure Blob Storage not configured"
            )
            return False, 0

        stored_filename = f"{uuid4()}{file_ext}"
        try:
            blob_path, blob_url, checksum, stored_size = blob_service.upload_file(
                container=settings.azure_container_uploads,
                file_data=content,
                filename=stored_filename,
                folder="scraped",
                metadata={
                    "upload_source": "scraper",
                    "original_url": page.url,
                    "content_type": content_type,
                    "scrape_url_id": str(scrape_url.id),
                },
            )
        except Exception as e:
            await job_service.add_log(
                job_id, LogLevel.ERROR, f"Blob upload failed for {page.url}: {str(e)}"
            )
            return False, 0

        # Step 4: Create DocumentRegistry entry
        jurisdiction = scrape_url.jurisdiction or "federal"
        try:
            registry = await registry_service.create_for_upload(
                document_name=filename,
                source_url=page.url,
                title=page.title or filename,
                jurisdiction=jurisdiction,
                state=scrape_url.state,
                city=scrape_url.city,
            )
            await registry_service.create_blob(
                registry_id=registry.id,
                blob_type="raw",
                blob_container=settings.azure_container_uploads,
                blob_path=blob_path,
                blob_url=blob_url,
                original_filename=filename,
                file_size=len(content),
                mime_type=content_type,
                content_hash=checksum,
            )
            await registry_service.update_processing_status(
                registry.id, ProcessingStatus.PROCESSING
            )
        except Exception as e:
            await job_service.add_log(
                job_id,
                LogLevel.ERROR,
                f"Registry creation failed for {page.url}: {str(e)}",
            )
            return False, 0

        # Steps 5-9: Extract, classify, create Solr doc, chunk, update status
        # Delegated to the shared ingestion pipeline.
        scrape_metadata = {
            "title": page.title,
            "source_url": page.url,
            "source_domain": urlparse(page.url).netloc if page.url else None,
            "jurisdiction": jurisdiction,
            "state": scrape_url.state,
            "city": scrape_url.city,
        }

        success, chunks_created = await process_from_content(
            registry_id=str(registry.id),
            file_content=content,
            filename=filename,
            content_type=content_type,
            metadata=scrape_metadata,
            source="scrape",
        )

        await job_service.add_log(
            job_id,
            LogLevel.INFO if success else LogLevel.WARNING,
            f"Processed: {page.url} -> {chunks_created} chunks"
            + ("" if success else " (failed)"),
        )

        return success, chunks_created

    except Exception as e:
        await job_service.add_log(
            job_id, LogLevel.ERROR, f"Unexpected error processing {page.url}: {str(e)}"
        )
        return False, 0


async def _download_page(
    url: str, timeout: int = 30
) -> Tuple[Optional[bytes], str, int]:
    """
    Download a page via HTTP GET.

    Returns:
        Tuple of (content_bytes or None, content_type, status_code)
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": "EverLeagues-Tax-KB-Scraper/1.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        ) as client:
            response = await client.get(url)
            content_type = response.headers.get("content-type", "application/octet-stream")
            content_type = content_type.split(";")[0].strip()

            if response.status_code >= 400:
                return None, content_type, response.status_code

            return response.content, content_type, response.status_code
    except httpx.TimeoutException:
        return None, "", 408
    except Exception:
        return None, "", 0


def _determine_filename(url: str, content_type: str) -> Tuple[str, str]:
    """
    Determine a filename and extension from URL and content type.

    Returns:
        Tuple of (filename, extension)
    """
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    # Try to get extension from URL path
    _, ext = os.path.splitext(path)
    if ext and ext.lower() in DOCUMENT_EXTENSIONS:
        basename = os.path.basename(path)
        return basename, ext.lower()

    # Fall back to content type mapping
    ext = CONTENT_TYPE_EXTENSIONS.get(content_type, ".html")
    basename = os.path.basename(path) if path and path != "/" else "page"
    if not basename:
        basename = "page"

    return f"{basename}{ext}", ext
