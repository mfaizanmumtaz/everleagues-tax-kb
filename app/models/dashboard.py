"""Pydantic models for dashboard operations."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ==================== Dashboard Models ====================


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
    ontology_stats: Optional[OntologyStats] = Field(
        default=None,
        description="Ontology graph stats (when Neo4j is configured)",
    )


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


# ==================== Freshness Models ====================


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


# ==================== Scalability Models ====================


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
