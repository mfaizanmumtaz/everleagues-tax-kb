"""Chunk API routes."""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List
from ..models.chunk import (
    ChunkCreate,
    ChunkUpdate,
    ChunkResponse,
    ChunkListResponse,
    BulkChunkCreate,
    BulkChunkResponse,
)
from ..models.common import FilterParams, GovernanceState
from ..services.chunk_service import get_chunk_service

router = APIRouter(prefix="/chunks", tags=["Chunks"])


@router.get("", response_model=ChunkListResponse)
async def list_chunks(
    query: str = Query(default="*:*", description="Search query"),
    document_id: Optional[str] = Query(default=None, description="Filter by document ID"),
    jurisdiction: Optional[str] = Query(default=None, description="Filter by jurisdiction"),
    state: Optional[str] = Query(default=None, description="Filter by state"),
    tax_year: Optional[int] = Query(default=None, description="Filter by tax year"),
    category: Optional[List[str]] = Query(default=None, description="Filter by category"),
    authority_level: Optional[int] = Query(default=None, ge=1, le=6, description="Filter by authority level"),
    governance_state: Optional[GovernanceState] = Query(default=None, description="Filter by governance state"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    sort: str = Query(default="chunkIndex asc", description="Sort field and direction"),
):
    """
    List chunks with filters and pagination.
    """
    try:
        service = get_chunk_service()
        
        filters = FilterParams(
            jurisdiction=jurisdiction,
            state=state,
            tax_year=tax_year,
            category=category,
            authority_level=authority_level,
            governance_state=governance_state,
        )
        
        chunks, total = service.list_chunks(
            query=query,
            document_id=document_id,
            filters=filters,
            page=page,
            limit=limit,
            sort=sort,
        )
        
        pages = (total + limit - 1) // limit
        
        return ChunkListResponse(
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


@router.get("/{chunk_id}", response_model=ChunkResponse)
async def get_chunk(
    chunk_id: str = Path(..., description="Chunk ID"),
):
    """
    Get a single chunk by ID.
    """
    try:
        service = get_chunk_service()
        chunk = service.get_chunk(chunk_id)
        
        if not chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        return chunk
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ChunkResponse, status_code=201)
async def create_chunk(
    chunk: ChunkCreate,
    generate_embedding: bool = Query(default=True, description="Auto-generate embedding"),
):
    """
    Create a new chunk.
    
    Optionally generates embedding vector if not provided.
    """
    try:
        service = get_chunk_service()
        result = service.create_chunk(chunk, generate_embedding=generate_embedding)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk", response_model=BulkChunkResponse, status_code=201)
async def create_chunks_bulk(request: BulkChunkCreate):
    """
    Create multiple chunks in bulk.
    
    Optionally generates embeddings for all chunks.
    """
    try:
        service = get_chunk_service()
        result = service.create_chunks_bulk(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{chunk_id}", response_model=ChunkResponse)
async def update_chunk(
    chunk_id: str = Path(..., description="Chunk ID"),
    updates: ChunkUpdate = ...,
):
    """
    Update a chunk.
    """
    try:
        service = get_chunk_service()
        chunk = service.update_chunk(chunk_id, updates)
        
        if not chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        return chunk
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chunk_id}", status_code=204)
async def delete_chunk(
    chunk_id: str = Path(..., description="Chunk ID"),
):
    """
    Delete a chunk.
    """
    try:
        service = get_chunk_service()
        
        # Check if chunk exists
        chunk = service.get_chunk(chunk_id)
        if not chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        service.delete_chunk(chunk_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

