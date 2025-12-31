"""Search API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from ..models.search import (
    SearchRequest,
    SearchResponse,
    ChunkSearchParams,
    RetrievedChunk,
)
from ..models.common import FilterParams, PaginatedResponse
from ..services.search_service import get_search_service

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("/rag", response_model=SearchResponse)
async def rag_search(request: SearchRequest):
    """
    Perform RAG (Retrieval-Augmented Generation) search.
    
    Supports hybrid search combining:
    - BM25 lexical search
    - Vector semantic search
    - Authority level weighting
    
    Returns ranked chunks and grouped source documents.
    """
    try:
        service = get_search_service()
        result = service.search(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chunks", response_model=PaginatedResponse[RetrievedChunk])
async def search_chunks(
    query: Optional[str] = Query(default=None, description="Text query"),
    document_id: Optional[str] = Query(default=None, description="Filter by document ID"),
    jurisdiction: Optional[str] = Query(default=None, description="Filter by jurisdiction"),
    state: Optional[str] = Query(default=None, description="Filter by state"),
    tax_year: Optional[int] = Query(default=None, description="Filter by tax year"),
    category: Optional[List[str]] = Query(default=None, description="Filter by category"),
    authority_level: Optional[int] = Query(default=None, ge=1, le=6, description="Filter by authority level"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    """
    Search chunks with filters and pagination.
    
    Returns paginated list of chunks matching the query and filters.
    """
    try:
        service = get_search_service()
        
        filters = FilterParams(
            jurisdiction=jurisdiction,
            state=state,
            tax_year=tax_year,
            category=category,
            authority_level=authority_level,
        )
        
        chunks, total = service.search_chunks(
            query=query,
            document_id=document_id,
            filters=filters,
            page=page,
            limit=limit,
        )
        
        pages = (total + limit - 1) // limit
        
        return PaginatedResponse(
            items=chunks,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

