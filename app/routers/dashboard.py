"""Dashboard API routes."""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..services.solr_service import get_solr_service
from ..database.connection import get_db
from ..db_models.scrape_url import ScrapeUrl, UrlStatus
from ..db_models.scrape_job import ScrapeJob, JobStatus

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class DashboardStats(BaseModel):
    """Dashboard statistics response."""

    total_documents: int = Field(description="Total number of documents")
    total_chunks: int = Field(description="Total number of chunks")
    total_tokens: int = Field(description="Total tokens indexed")
    documents_by_governance: Dict[str, int] = Field(
        description="Documents by governance state"
    )
    documents_by_sync_status: Dict[str, int] = Field(
        description="Documents by sync status"
    )
    documents_by_index_status: Dict[str, int] = Field(
        description="Documents by index status"
    )
    documents_by_jurisdiction: Dict[str, int] = Field(
        description="Documents by jurisdiction"
    )
    chunks_by_jurisdiction: Dict[str, int] = Field(description="Chunks by jurisdiction")
    chunks_by_tax_year: Dict[str, int] = Field(description="Chunks by tax year")


class RAGHealthMetrics(BaseModel):
    """RAG system health metrics."""

    solr_documents_healthy: bool = Field(description="Documents collection is healthy")
    solr_chunks_healthy: bool = Field(description="Chunks collection is healthy")
    indexed_documents: int = Field(description="Number of indexed documents")
    indexed_chunks: int = Field(description="Number of indexed chunks")
    avg_chunks_per_document: float = Field(description="Average chunks per document")
    avg_tokens_per_chunk: float = Field(description="Average tokens per chunk")
    coverage_by_jurisdiction: Dict[str, int] = Field(
        description="Document count by jurisdiction"
    )
    coverage_by_tax_year: Dict[str, int] = Field(
        description="Document count by tax year"
    )


class Alert(BaseModel):
    """System alert."""

    id: str
    level: str  # info, warning, error
    message: str
    timestamp: str
    resolved: bool = False


class AlertsResponse(BaseModel):
    """System alerts response."""

    alerts: List[Alert]
    total: int


def _parse_facet_counts(facet_fields: Dict, field_name: str) -> Dict[str, int]:
    """Parse Solr facet counts into a dictionary."""
    if not facet_fields or field_name not in facet_fields:
        return {}

    facet_list = facet_fields[field_name]
    result = {}

    # Solr returns alternating [value, count, value, count, ...]
    for i in range(0, len(facet_list), 2):
        if i + 1 < len(facet_list):
            value = str(facet_list[i]) if facet_list[i] else "unknown"
            count = facet_list[i + 1]
            result[value] = count

    return result


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """
    Get overall dashboard statistics.

    Returns document and chunk counts with breakdowns by various dimensions.
    """
    try:
        solr = get_solr_service()

        # Get document stats (async)
        doc_stats = await solr.get_document_stats()
        chunk_stats = await solr.get_chunk_stats()

        # Parse facet counts
        doc_facets = doc_stats.get("facets", {})
        chunk_facets = chunk_stats.get("facets", {})

        # Calculate total tokens
        token_stats = doc_stats.get("stats", {}).get("tokensIndexed", {})
        total_tokens = int(token_stats.get("sum", 0)) if token_stats else 0

        return DashboardStats(
            total_documents=doc_stats.get("total", 0),
            total_chunks=chunk_stats.get("total", 0),
            total_tokens=total_tokens,
            documents_by_governance=_parse_facet_counts(doc_facets, "governanceState"),
            documents_by_sync_status=_parse_facet_counts(doc_facets, "syncStatus"),
            documents_by_index_status=_parse_facet_counts(doc_facets, "indexStatus"),
            documents_by_jurisdiction=_parse_facet_counts(doc_facets, "jurisdiction"),
            chunks_by_jurisdiction=_parse_facet_counts(chunk_facets, "jurisdiction"),
            chunks_by_tax_year=_parse_facet_counts(chunk_facets, "taxYear"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag-health", response_model=RAGHealthMetrics)
async def get_rag_health():
    """
    Get RAG system health metrics.

    Returns collection health status and coverage metrics.
    """
    try:
        solr = get_solr_service()

        # Check collection health (async)
        health = await solr.health_check()

        # Get stats (async)
        doc_stats = await solr.get_document_stats()
        chunk_stats = await solr.get_chunk_stats()

        total_docs = doc_stats.get("total", 0)
        total_chunks = chunk_stats.get("total", 0)

        # Calculate averages
        avg_chunks = total_chunks / total_docs if total_docs > 0 else 0

        token_stats = chunk_stats.get("stats", {}).get("tokenCount", {})
        avg_tokens = token_stats.get("mean", 0) if token_stats else 0

        # Parse facets for coverage
        doc_facets = doc_stats.get("facets", {})
        chunk_facets = chunk_stats.get("facets", {})

        return RAGHealthMetrics(
            solr_documents_healthy=health.get("documents", False),
            solr_chunks_healthy=health.get("chunks", False),
            indexed_documents=total_docs,
            indexed_chunks=total_chunks,
            avg_chunks_per_document=round(avg_chunks, 2),
            avg_tokens_per_chunk=round(avg_tokens, 2),
            coverage_by_jurisdiction=_parse_facet_counts(doc_facets, "jurisdiction"),
            coverage_by_tax_year=_parse_facet_counts(chunk_facets, "taxYear"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts():
    """
    Get system alerts.

    Returns list of active and recent alerts.
    """
    try:
        solr = get_solr_service()

        alerts = []

        # Check Solr health (async)
        health = await solr.health_check()

        if not health.get("documents", False):
            alerts.append(
                Alert(
                    id="solr_documents_down",
                    level="error",
                    message="Solr tax_documents collection is not responding",
                    timestamp="",
                    resolved=False,
                )
            )

        if not health.get("chunks", False):
            alerts.append(
                Alert(
                    id="solr_chunks_down",
                    level="error",
                    message="Solr tax_chunks collection is not responding",
                    timestamp="",
                    resolved=False,
                )
            )

        # Check for documents needing review (async)
        try:
            docs, count = await solr.search_documents(
                query="needsHumanReview:true", rows=0
            )
            if count > 0:
                alerts.append(
                    Alert(
                        id="documents_need_review",
                        level="warning",
                        message=f"{count} document(s) need human review",
                        timestamp="",
                        resolved=False,
                    )
                )
        except Exception:
            pass

        # Check for sync/index failures (async)
        try:
            docs, sync_failed = await solr.search_documents(
                query="syncStatus:sync_failed", rows=0
            )
            if sync_failed > 0:
                alerts.append(
                    Alert(
                        id="sync_failures",
                        level="warning",
                        message=f"{sync_failed} document(s) failed to sync",
                        timestamp="",
                        resolved=False,
                    )
                )
        except Exception:
            pass

        try:
            docs, index_failed = await solr.search_documents(
                query="indexStatus:index_failed", rows=0
            )
            if index_failed > 0:
                alerts.append(
                    Alert(
                        id="index_failures",
                        level="warning",
                        message=f"{index_failed} document(s) failed to index",
                        timestamp="",
                        resolved=False,
                    )
                )
        except Exception:
            pass

        return AlertsResponse(
            alerts=alerts,
            total=len(alerts),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Freshness Endpoint ====================


class StaleDocument(BaseModel):
    """A document that has not been updated recently."""

    id: str
    name: str
    last_updated: str
    days_stale: int
    source_url: Optional[str] = None


class RecentUrlActivity(BaseModel):
    """Recent URL scraping activity."""

    id: str
    url: str
    last_scraped_at: Optional[str] = None
    status: str
    documents_count: int


class FreshnessMetrics(BaseModel):
    """Document freshness metrics."""

    docs_stale_over_30_days: int = 0
    docs_stale_over_1_year: int = 0
    docs_stale_over_2_years: int = 0
    urls_scraped_last_7_days: int = 0
    stale_documents: List[StaleDocument] = []
    recent_url_activity: List[RecentUrlActivity] = []


@router.get("/freshness", response_model=FreshnessMetrics)
async def get_freshness_metrics(db: AsyncSession = Depends(get_db)):
    """
    Get document freshness metrics.

    Queries Solr for stale documents and PostgreSQL for URL scraping activity.
    """
    try:
        solr = get_solr_service()
        now = datetime.now(timezone.utc)

        # Solr date queries for stale documents
        docs_30d = 0
        docs_1y = 0
        docs_2y = 0
        stale_docs_list: List[StaleDocument] = []

        try:
            # Count documents not updated in 30+ days
            _, docs_30d = await solr.search_documents(
                query="*:*",
                filters=["updatedAt:[* TO NOW-30DAY]"],
                rows=0,
            )
        except Exception:
            pass

        try:
            # Count documents not updated in 1+ year
            _, docs_1y = await solr.search_documents(
                query="*:*",
                filters=["updatedAt:[* TO NOW-365DAY]"],
                rows=0,
            )
        except Exception:
            pass

        try:
            # Count documents not updated in 2+ years
            _, docs_2y = await solr.search_documents(
                query="*:*",
                filters=["updatedAt:[* TO NOW-730DAY]"],
                rows=0,
            )
        except Exception:
            pass

        try:
            # Get top 10 stalest documents
            # Note: updatedAt lacks docValues in Solr, so we sort in Python instead
            stale_results, _ = await solr.search_documents(
                query="*:*",
                filters=["updatedAt:[* TO NOW-30DAY]"],
                fields=["id", "name", "updatedAt", "sourceUrl"],
                rows=50,
            )
            # Sort by updatedAt ascending (stalest first) in Python
            stale_results.sort(key=lambda d: d.get("updatedAt", ""), reverse=False)
            for doc in stale_results:
                updated_str = doc.get("updatedAt", "")
                days_stale = 0
                if updated_str:
                    try:
                        updated_dt = datetime.fromisoformat(
                            updated_str.replace("Z", "+00:00")
                        )
                        days_stale = (now - updated_dt).days
                    except Exception:
                        pass

                stale_docs_list.append(
                    StaleDocument(
                        id=doc.get("id", ""),
                        name=doc.get("name", "Unknown"),
                        last_updated=updated_str,
                        days_stale=days_stale,
                        source_url=doc.get("sourceUrl"),
                    )
                )
        except Exception:
            pass

        # PostgreSQL: URLs scraped in last 7 days
        seven_days_ago = now - timedelta(days=7)
        urls_scraped_count = 0
        recent_activity: List[RecentUrlActivity] = []

        try:
            count_result = await db.execute(
                select(func.count(ScrapeUrl.id)).where(
                    ScrapeUrl.last_scraped_at >= seven_days_ago
                )
            )
            urls_scraped_count = count_result.scalar() or 0

            # Recent URL activity (top 10 most recently updated)
            url_result = await db.execute(
                select(ScrapeUrl)
                .order_by(ScrapeUrl.updated_at.desc())
                .limit(10)
            )
            for url in url_result.scalars().all():
                recent_activity.append(
                    RecentUrlActivity(
                        id=str(url.id),
                        url=url.url,
                        last_scraped_at=url.last_scraped_at.isoformat()
                        if url.last_scraped_at
                        else None,
                        status=url.status.value if url.status else "active",
                        documents_count=url.documents_count or 0,
                    )
                )
        except Exception:
            pass

        return FreshnessMetrics(
            docs_stale_over_30_days=docs_30d,
            docs_stale_over_1_year=docs_1y,
            docs_stale_over_2_years=docs_2y,
            urls_scraped_last_7_days=urls_scraped_count,
            stale_documents=stale_docs_list,
            recent_url_activity=recent_activity,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Scalability Endpoint ====================


class ScalabilityMetrics(BaseModel):
    """System scalability metrics."""

    total_documents: int = 0
    total_chunks: int = 0
    total_urls: int = 0
    active_urls: int = 0
    total_jobs_last_24h: int = 0
    documents_processed_last_24h: int = 0
    avg_job_duration_seconds: float = 0.0
    job_success_rate: float = 0.0
    documents_by_status: Dict[str, int] = {}


@router.get("/scalability", response_model=ScalabilityMetrics)
async def get_scalability_metrics(db: AsyncSession = Depends(get_db)):
    """
    Get system scalability metrics.

    Queries Solr for document/chunk counts and PostgreSQL for URL/job statistics.
    """
    try:
        solr = get_solr_service()
        now = datetime.now(timezone.utc)
        twenty_four_hours_ago = now - timedelta(hours=24)

        # Solr counts
        total_documents = 0
        total_chunks = 0
        docs_by_status: Dict[str, int] = {}

        try:
            doc_stats = await solr.get_document_stats()
            chunk_stats = await solr.get_chunk_stats()
            total_documents = doc_stats.get("total", 0)
            total_chunks = chunk_stats.get("total", 0)

            doc_facets = doc_stats.get("facets", {})
            docs_by_status = _parse_facet_counts(doc_facets, "indexStatus")
        except Exception:
            pass

        # PostgreSQL: URL counts
        total_urls = 0
        active_urls = 0

        try:
            total_result = await db.execute(select(func.count(ScrapeUrl.id)))
            total_urls = total_result.scalar() or 0

            active_result = await db.execute(
                select(func.count(ScrapeUrl.id)).where(
                    ScrapeUrl.status == UrlStatus.ACTIVE
                )
            )
            active_urls = active_result.scalar() or 0
        except Exception:
            pass

        # PostgreSQL: Job stats (last 24h)
        total_jobs_24h = 0
        docs_processed_24h = 0
        avg_duration = 0.0
        success_rate = 0.0

        try:
            # Total jobs in last 24h
            jobs_count_result = await db.execute(
                select(func.count(ScrapeJob.id)).where(
                    ScrapeJob.created_at >= twenty_four_hours_ago
                )
            )
            total_jobs_24h = jobs_count_result.scalar() or 0

            # Documents processed in last 24h
            docs_result = await db.execute(
                select(func.coalesce(func.sum(ScrapeJob.documents_created), 0)).where(
                    ScrapeJob.created_at >= twenty_four_hours_ago
                )
            )
            docs_processed_24h = docs_result.scalar() or 0

            # Average job duration (completed jobs)
            avg_result = await db.execute(
                select(func.avg(ScrapeJob.duration_seconds)).where(
                    ScrapeJob.status == JobStatus.COMPLETED,
                    ScrapeJob.duration_seconds.isnot(None),
                )
            )
            avg_val = avg_result.scalar()
            avg_duration = round(float(avg_val), 2) if avg_val else 0.0

            # Success rate (all time)
            total_finished = await db.execute(
                select(func.count(ScrapeJob.id)).where(
                    ScrapeJob.status.in_([
                        JobStatus.COMPLETED,
                        JobStatus.FAILED,
                        JobStatus.CANCELLED,
                    ])
                )
            )
            finished_count = total_finished.scalar() or 0

            completed_count_result = await db.execute(
                select(func.count(ScrapeJob.id)).where(
                    ScrapeJob.status == JobStatus.COMPLETED
                )
            )
            completed_count = completed_count_result.scalar() or 0

            if finished_count > 0:
                success_rate = round((completed_count / finished_count) * 100, 1)
        except Exception:
            pass

        return ScalabilityMetrics(
            total_documents=total_documents,
            total_chunks=total_chunks,
            total_urls=total_urls,
            active_urls=active_urls,
            total_jobs_last_24h=total_jobs_24h,
            documents_processed_last_24h=docs_processed_24h,
            avg_job_duration_seconds=avg_duration,
            job_success_rate=success_rate,
            documents_by_status=docs_by_status,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
