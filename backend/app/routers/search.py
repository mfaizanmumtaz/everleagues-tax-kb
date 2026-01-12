"""Search API routes."""

from fastapi import APIRouter, HTTPException
from ..models.search import SearchRequest, SearchResponse
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
