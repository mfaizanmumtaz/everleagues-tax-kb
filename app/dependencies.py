"""Shared dependencies for FastAPI application."""

from .services.solr_service import SolrService, get_solr_service
from .services.search_service import SearchService, get_search_service
from .services.document_service import DocumentService, get_document_service
from .services.chunk_service import ChunkService, get_chunk_service
from .services.embedding_service import EmbeddingService, get_embedding_service


def get_solr() -> SolrService:
    """Dependency to get Solr service."""
    return get_solr_service()


def get_search() -> SearchService:
    """Dependency to get search service."""
    return get_search_service()


def get_documents() -> DocumentService:
    """Dependency to get document service."""
    return get_document_service()


def get_chunks() -> ChunkService:
    """Dependency to get chunk service."""
    return get_chunk_service()


def get_embeddings() -> EmbeddingService:
    """Dependency to get embedding service."""
    return get_embedding_service()
