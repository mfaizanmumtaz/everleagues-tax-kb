"""Dashboard API routes."""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from ..services.solr_service import get_solr_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class DashboardStats(BaseModel):
    """Dashboard statistics response."""
    total_documents: int = Field(description="Total number of documents")
    total_chunks: int = Field(description="Total number of chunks")
    total_tokens: int = Field(description="Total tokens indexed")
    documents_by_governance: Dict[str, int] = Field(description="Documents by governance state")
    documents_by_sync_status: Dict[str, int] = Field(description="Documents by sync status")
    documents_by_index_status: Dict[str, int] = Field(description="Documents by index status")
    documents_by_jurisdiction: Dict[str, int] = Field(description="Documents by jurisdiction")
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
    coverage_by_jurisdiction: Dict[str, int] = Field(description="Document count by jurisdiction")
    coverage_by_tax_year: Dict[str, int] = Field(description="Document count by tax year")


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
        
        # Get document stats
        doc_stats = solr.get_document_stats()
        chunk_stats = solr.get_chunk_stats()
        
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
        
        # Check collection health
        health = solr.health_check()
        
        # Get stats
        doc_stats = solr.get_document_stats()
        chunk_stats = solr.get_chunk_stats()
        
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
        
        # Check Solr health
        health = solr.health_check()
        
        if not health.get("documents", False):
            alerts.append(Alert(
                id="solr_documents_down",
                level="error",
                message="Solr tax_documents collection is not responding",
                timestamp="",
                resolved=False,
            ))
        
        if not health.get("chunks", False):
            alerts.append(Alert(
                id="solr_chunks_down",
                level="error",
                message="Solr tax_chunks collection is not responding",
                timestamp="",
                resolved=False,
            ))
        
        # Check for documents needing review
        try:
            docs, count = solr.search_documents(
                query="needsHumanReview:true",
                rows=0
            )
            if count > 0:
                alerts.append(Alert(
                    id="documents_need_review",
                    level="warning",
                    message=f"{count} document(s) need human review",
                    timestamp="",
                    resolved=False,
                ))
        except Exception:
            pass
        
        # Check for sync/index failures
        try:
            docs, sync_failed = solr.search_documents(
                query="syncStatus:sync_failed",
                rows=0
            )
            if sync_failed > 0:
                alerts.append(Alert(
                    id="sync_failures",
                    level="warning",
                    message=f"{sync_failed} document(s) failed to sync",
                    timestamp="",
                    resolved=False,
                ))
        except Exception:
            pass
        
        try:
            docs, index_failed = solr.search_documents(
                query="indexStatus:index_failed",
                rows=0
            )
            if index_failed > 0:
                alerts.append(Alert(
                    id="index_failures",
                    level="warning",
                    message=f"{index_failed} document(s) failed to index",
                    timestamp="",
                    resolved=False,
                ))
        except Exception:
            pass
        
        return AlertsResponse(
            alerts=alerts,
            total=len(alerts),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

